# models.py (sketch)
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, TEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
import uuid, datetime
from pathlib import Path
from enum import Enum as PyEnum
from sqlalchemy import Enum as SQLEnum

# PROJECT_ROOT: adjust depending where models.py sits.
# If models.py is at repo_root/backend/db/models.py, then:
PROJECT_ROOT = Path(__file__).resolve().parents[2]   # repo_root

# explicit DB file under backend folder
DB_FILE = PROJECT_ROOT / "backend" / "mediahub.db"

# Construct an absolute sqlite URL. Note 3 slashes + absolute path on Unix: sqlite:////abs/path
DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # usually helpful for web apps + threads
    echo=False,
)

Base = declarative_base()
def genid(): return str(uuid.uuid4())
def now(): return datetime.datetime.now()

# Define possible fetch statuses
class FetchStatus(PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    FETCHED = "fetched"      # successfully fetched metadata
    NOT_FOUND = "not_found"  # page not found / selectors missing
    FAILED = "failed"        # attempted but failed (network/error)

class Library(Base):
    __tablename__ = "library"
    id = Column(String, primary_key=True, default=genid)
    name = Column(String, default="My Library")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

class RootFolder(Base):
    __tablename__ = "root_folder"
    id = Column(String, primary_key=True, default=genid)
    library_id = Column(String, ForeignKey("library.id"))
    path = Column(String, unique=True, nullable=False)
    label = Column(String)
    status = Column(String, default="idle")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

class MediaFile(Base):
    __tablename__ = "media_file"
    id = Column(String, primary_key=True, default=genid)
    root_folder_id = Column(String, ForeignKey("root_folder.id"), index=True)
    path = Column(String, unique=True, nullable=False)
    filename = Column(String, index=True)
    filesize = Column(Integer)
    mtime = Column(Integer) #modified time
    is_indexed = Column(Boolean, default=False)
    metadata_ = Column(JSON, default={})
    last_watched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

class JavMetadata(Base):
    __tablename__ = "jav_metadata"
    code = Column(String, primary_key=True)                   # e.g., NAFZ-001
    metadata_json = Column(JSON, default={})                  # full metadata as JSON
    source_url = Column(String, nullable=True)
    fetched_at = Column(DateTime, default=now, onupdate=now)

    # Status column: stored as text in DB (native_enum=False is portable, esp. for SQLite)
    status = Column(
        SQLEnum(FetchStatus, native_enum=False, length=50),
        default=FetchStatus.FETCHED,
        nullable=False,
        server_default=FetchStatus.FETCHED.value
    )

class MetadataJob(Base):
    __tablename__ = "metadata_job"
    id = Column(String, primary_key=genid, default=genid)
    media_file_id = Column(String, ForeignKey("media_file.id"), nullable=True, index=True)
    code = Column(String, index=True, nullable=True)          # optional: fetch by code
    params = Column(JSON, default={})                         # e.g., {"force": True}
    status = Column(String, default="queued")                 # queued, running, done, failed
    attempt = Column(Integer, default=0)
    notes = Column(TEXT, default="")
    created_at = Column(DateTime, default=now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)
