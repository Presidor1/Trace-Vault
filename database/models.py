# tracevault/database/models.py

import uuid
from sqlalchemy import create_engine, Column, String, Text, DateTime, Float, Integer, ForeignKey, JSON, Enum
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import enum

# --- Setup Declarative Base ---
Base = declarative_base()

# --- Utility Functions ---
# Placeholder function for establishing connection (will be called in app.py)
def init_db(database_url: str):
    """Initializes the database engine and creates tables."""
    # The 'postgresql+psycopg2://' dialect is standard for Render Postgres
    engine = create_engine(database_url)
    
    # Create tables defined by Base (only runs if tables don't exist)
    Base.metadata.create_all(engine)
    
    # Return a configured Session factory
    Session = sessionmaker(bind=engine)
    return Session, engine


# --- Enums for Status Tracking ---
class AnalysisStatus(enum.Enum):
    """Defines the current processing status of an evidence item."""
    PENDING = 'PENDING'
    METADATA_EXTRACTED = 'METADATA_EXTRACTED'
    FRAMES_EXTRACTED = 'FRAMES_EXTRACTED'
    ANALYSIS_COMPLETE = 'ANALYSIS_COMPLETE'
    FAILED = 'FAILED'
    
class MediaType(enum.Enum):
    """Defines the media type of the evidence."""
    IMAGE = 'IMAGE'
    VIDEO = 'VIDEO'
    DOCUMENT = 'DOCUMENT'
    OTHER = 'OTHER'


# --- 1. Evidence Table (The Root Record) ---
class Evidence(Base):
    """Represents a single piece of uploaded evidence (image, video, or document)."""
    __tablename__ = 'evidence'

    # The primary key, using UUID for distributed systems
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    original_filename = Column(String(255), nullable=False)
    # The path where the original file is stored (e.g., S3 URL or /tmp/path)
    storage_path = Column(Text, nullable=False)
    
    media_type = Column(Enum(MediaType), default=MediaType.OTHER, nullable=False)
    
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)
    
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships (Cascading deletes ensure related data is removed when evidence is deleted)
    metadata_report = relationship("MetadataReport", back_populates="evidence", uselist=False, cascade="all, delete-orphan")
    frames = relationship("Frame", back_populates="evidence", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Evidence(id='{self.id}', filename='{self.original_filename}', status='{self.status.value}')>"


# --- 2. Metadata Extraction Table ---
class MetadataReport(Base):
    """Stores data extracted by metadata_worker.py (EXIF, OCR)."""
    __tablename__ = 'metadata_reports'
    
    id = Column(Integer, primary_key=True)
    evidence_id = Column(String(36), ForeignKey('evidence.id'), unique=True, nullable=False)
    
    # Key-value JSON blob from ExifTool
    extracted_metadata = Column(JSON, nullable=True) 
    
    # Full text extracted via OCR
    ocr_text = Column(Text, nullable=True)
    
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship back to Evidence
    evidence = relationship("Evidence", back_populates="metadata_report")


# --- 3. Video Frame Table ---
class Frame(Base):
    """Stores records for individual frames extracted from a video."""
    __tablename__ = 'frames'
    
    id = Column(Integer, primary_key=True)
    evidence_id = Column(String(36), ForeignKey('evidence.id'), nullable=False)
    
    # The storage path of the *extracted frame* image file (e.g., S3 URL or /tmp/path)
    frame_storage_path = Column(Text, nullable=False)
    
    # The time in seconds from the start of the video
    timestamp_sec = Column(Float, nullable=True) 
    
    # Relationships
    evidence = relationship("Evidence", back_populates="frames")
    faces = relationship("FaceEmbedding", back_populates="frame", cascade="all, delete-orphan")
    scene_analysis = relationship("SceneAnalysis", back_populates="frame", uselist=False, cascade="all, delete-orphan")


# --- 4. Face Embedding Table ---
class FaceEmbedding(Base):
    """Stores the vector, bounding box, and attributes for a detected face."""
    __tablename__ = 'face_embeddings'
    
    id = Column(Integer, primary_key=True)
    frame_id = Column(Integer, ForeignKey('frames.id'), nullable=False)
    
    # The 512-dimensional vector (or whatever the model uses)
    embedding_vector = Column(JSON, nullable=False) 
    
    # Bounding Box (x, y, w, h)
    bounding_box = Column(JSON, nullable=False)
    
    # Attributes (age, gender, emotion, etc.)
    attributes = Column(JSON, nullable=True)
    
    # Relationship
    frame = relationship("Frame", back_populates="faces")


# --- 5. Scene Analysis Table ---
class SceneAnalysis(Base):
    """Stores the results of scene classification for a frame."""
    __tablename__ = 'scene_analyses'
    
    id = Column(Integer, primary_key=True)
    frame_id = Column(Integer, ForeignKey('frames.id'), unique=True, nullable=False)
    
    # The top-k scenes and their confidence scores
    classification_scores = Column(JSON, nullable=False)
    
    # Relationship
    frame = relationship("Frame", back_populates="scene_analysis")


# --- Test Block (Simple) ---
if __name__ == '__main__':
    # This block allows local testing of the model definitions
    print("Database models defined successfully.")
    print(f"Total tables defined: {len(Base.metadata.tables)}")
    print("To test creation, run init_db() with a valid connection string.")
  
