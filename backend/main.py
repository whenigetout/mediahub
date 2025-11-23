# main.py
from fastapi import FastAPI, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
from db.models import Library, RootFolder, MediaFile, engine
from pathlib import Path
import datetime
from contextlib import asynccontextmanager
import threading
from pydantic import BaseModel
from typing import List, Optional

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# ---------- helpers ----------
def now():
    return datetime.datetime.now()

def get_or_create_library():
    db = SessionLocal()
    lib = db.query(Library).first()
    if not lib:
        lib = Library(name="My Library")
        db.add(lib)
        db.commit()
        db.refresh(lib)
    db.close()
    return lib

# ---------- on app start ----------
@asynccontextmanager
async def ensure_library_on_startup(app: FastAPI):
    # startup
    get_or_create_library()

    # start a background thread to scan everything (non-blocking startup)
    def _startup_scan_thread():
        try:
            print("startup: launching initial library scan")
            scan_all_roots()
            print("startup: initial scan finished")
        except Exception as e:
            print("startup: scan failed", e)
    
    t = threading.Thread(target=_startup_scan_thread, daemon=True)
    t.start()

    yield
    # Clean up, if any

app = FastAPI(title="MediaHub API", lifespan=ensure_library_on_startup)

# ---------- scan worker (sync) ----------
def scan_root_sync(root_folder_id: str, commit_every: int = 200):
    """
    Walk the root folder, upsert media_files based on path,
    skip unchanged files by checking mtime + size, and delete missing rows.
    Runs in a background thread/task.
    """
    db = SessionLocal()
    try:
        root_folder = db.query(RootFolder).filter_by(id=root_folder_id).first()
        if not root_folder:
            return

        root_folder.status = "scanning"
        root_folder.updated_at = now()
        db.commit()

        base = Path(root_folder.path)
        if not base.exists() or not base.is_dir():
            root_folder.status = "error"
            root_folder.updated_at = now()
            db.commit()
            return

        seen_paths = set()
        counter = 0
        # Walk files recursively
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            try:
                st = p.stat()
            except (OSError, PermissionError):
                # skip files we can't stat
                continue

            full_path = str(p)
            seen_paths.add(full_path)
            mtime = int(st.st_mtime)
            size = int(st.st_size)

            existing = db.query(MediaFile).filter_by(path=full_path).first()
            if existing:
                # quick skip if unchanged
                if existing.mtime == mtime and (existing.filesize or 0) == size:
                    continue
                # update metadata-lite and mark for re-index
                existing.filesize = size
                existing.mtime = mtime
                existing.is_indexed = False
                existing.updated_at = now()
                db.add(existing)
            else:
                mf = MediaFile(
                    root_folder_id=root_folder.id,
                    path=full_path,
                    filename=p.name,
                    filesize=size,
                    mtime=mtime,
                    is_indexed=False,
                    created_at=now(),
                    updated_at=now(),
                )
                db.add(mf)

            counter += 1
            if counter % commit_every == 0:
                db.commit()

        # commit remaining
        db.commit()

        # Cleanup: remove DB rows for files no longer present under this root
        # (optional: you could instead mark missing; this physically deletes)
        rows = db.query(MediaFile).filter_by(root_folder_id=root_folder.id).all()
        for r in rows:
            if r.path not in seen_paths:
                db.delete(r)
        db.commit()

        root_folder.status = "idle"
        root_folder.updated_at = now()
        db.commit()
    finally:
        db.close()

# --- helper that runs the scans synchronously (callable from anywhere) ---
def scan_all_roots():
    db = SessionLocal()
    try:
        roots = db.query(RootFolder).all()
        for r in roots:
            # call sync worker directly (blocking for each root)
            try:
                scan_root_sync(r.id)
            except Exception as e:
                # swallow/log errors so one bad root doesn't stop others
                print("scan_root_sync error for", r.path, e)
    finally:
        db.close()


# ---------- endpoints ----------

@app.get("/library")
def get_library():
    db = SessionLocal()
    lib = db.query(Library).first()
    roots = db.query(RootFolder).filter_by(library_id=lib.id).all() if lib else []
    db.close()
    return {"library": lib, "roots": roots}

@app.get("/library/root_folders")
def list_roots():
    db = SessionLocal()
    roots = db.query(RootFolder).order_by(RootFolder.label).all()
    db.close()
    return {"roots": roots}

@app.post("/library/add_root_folder")
def add_root(path: str = Query(..., description="Absolute folder path"), label: str | None = None):
    folder = Path(path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist or is not a folder")

    db = SessionLocal()
    lib = db.query(Library).first()
    if not lib:
        lib = Library(name="My Library")
        db.add(lib)
        db.commit()
        db.refresh(lib)

    # avoid duplicate root paths
    existing = db.query(RootFolder).filter_by(path=str(folder)).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Root folder already added")

    root = RootFolder(library_id=lib.id, path=str(folder), label=label or folder.name, status="idle", created_at=now(), updated_at=now())
    db.add(root)
    db.commit()
    db.refresh(root)
    db.close()
    return {"root": {"id": root.id, "path": root.path, "label": root.label}}


@app.delete("/library/root_folders/{root_folder_id}")
def delete_root(root_folder_id: str, delete_files: bool = Query(False, description="Also delete associated media_file rows")):
    db = SessionLocal()
    root = db.query(RootFolder).filter_by(id=root_folder_id).first()
    if not root:
        db.close()
        raise HTTPException(status_code=404, detail="Root folder not found")
    if delete_files:
        db.query(MediaFile).filter_by(root_folder_id=root.id).delete()
    db.delete(root)
    db.commit()
    db.close()
    return {"status": "deleted"}


@app.post("/library/root_folders/{root_folder_id}/scan")
def scan_root_folder(root_folder_id: str, background_tasks: BackgroundTasks):
    db = SessionLocal()
    root = db.query(RootFolder).filter_by(id=root_folder_id).first()
    db.close()
    if not root:
        raise HTTPException(status_code=404, detail="Root folder not found")
    background_tasks.add_task(scan_root_sync, root_folder_id)
    return {"status": "scan_queued", "root_folder_id": root_folder_id}


@app.post("/library/scan_all")
def scan_all(background_tasks: BackgroundTasks):
    db = SessionLocal()
    roots = db.query(RootFolder).all()
    db.close()
    for r in roots:
        background_tasks.add_task(scan_root_sync, r.id)
    return {"status": "queued", "count": len(roots)}


@app.get("/library/files")
def list_files(root_folder_ids: str | None = Query(None, description="Comma-separated root folder ids"), q: str | None = Query(None), limit: int = 200, offset: int = 0):
    """
    Query params:
      - roots=comma,separated,ids  (optional)
      - q=search string (optional, will run a simple LIKE on filename)
      - limit, offset
    """
    db = SessionLocal()
    q_base = db.query(MediaFile)
    if root_folder_ids:
        ids = [r.strip() for r in root_folder_ids.split(",") if r.strip()]
        q_base = q_base.filter(MediaFile.root_folder_id.in_(ids))
    if q:
        # simple case-insensitive match on filename
        like = f"%{q}%"
        q_base = q_base.filter(MediaFile.filename.ilike(like))
    total = q_base.count()
    rows = q_base.order_by(MediaFile.filename).offset(offset).limit(limit).all()
    db.close()

    files = [
        {
            "id": r.id,
            "path": r.path,
            "filename": r.filename,
            "filesize": r.filesize,
            "mtime": r.mtime,
            "is_indexed": bool(r.is_indexed),
            "last_watched_at": r.last_watched_at,
        }
        for r in rows
    ]
    return {"count": total, "files": files}


@app.post("/library/files/{file_id}/mark_watched")
def mark_watched(file_id: str):
    db = SessionLocal()
    r = db.query(MediaFile).filter_by(id=file_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="file not found")
    r.last_watched_at = now()
    r.updated_at = now()
    db.add(r)
    db.commit()
    db.close()
    return {"status": "ok", "id": file_id, "last_watched_at": r.last_watched_at}


@app.post("/library/clear")
def clear_library():
    db = SessionLocal()
    # remove all media files and root folders but keep library metadata
    deleted = db.query(MediaFile).delete()
    deleted = db.query(RootFolder).delete()
    db.commit()
    db.close()
    return {"status": "cleared", "deleted_rows": deleted}

class ListDirReq(BaseModel):
    path: str
    include_files: Optional[bool] = False   # default: only directories
    max_entries: Optional[int] = 1000      # safety limit
    show_hidden: Optional[bool] = False    # include dotfiles if true

class DirEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    filesize: Optional[int] = None
    mtime: Optional[int] = None

class ListDirResp(BaseModel):
    ok: bool = True
    entries: List[DirEntry]

@app.post("/library/list_dir", response_model=ListDirResp)
def list_dir(req: ListDirReq):
    p = Path(req.path)

    # Resolve and validate path exists
    try:
        p_resolved = p.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Path not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    if not p_resolved.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    try:
        # iterate children sorted by name
        for child in sorted(p_resolved.iterdir(), key=lambda x: x.name.lower()):
            # skip hidden entries unless requested
            if not req.show_hidden and child.name.startswith("."):
                continue

            is_dir = False
            try:
                is_dir = child.is_dir()
            except (OSError, PermissionError):
                # If we can't stat it, skip or include minimal info
                # we'll include a placeholder entry with is_dir=False (safe default)
                is_dir = False

            # if we only want directories, skip files here
            if not req.include_files and not is_dir:
                continue

            filesize = None
            mtime = None
            if child.is_file():
                try:
                    st = child.stat()
                    filesize = int(st.st_size)
                    mtime = int(st.st_mtime)
                except (OSError, PermissionError):
                    filesize = None
                    mtime = None

            entries.append({
                "name": child.name,
                "path": str(child.resolve()) if child.exists() else str(child),
                "is_dir": is_dir,
                "filesize": filesize,
                "mtime": mtime,
            })

            # safety: stop if we reached max_entries
            if req.max_entries and len(entries) >= req.max_entries:
                break

    except (PermissionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Could not list directory: {e}")

    return {"ok": True, "entries": entries}
