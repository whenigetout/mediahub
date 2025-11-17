# models.py (sketch)
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, TEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
import uuid, datetime

Base = declarative_base()
def genid(): return str(uuid.uuid4())
def now(): return datetime.datetime.now()

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


engine = create_engine("sqlite:///./mediahub.db", connect_args={"check_same_thread": False})
# Base.metadata.create_all(bind=engine)
