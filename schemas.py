"""
Database Schemas for AI Song Generator

Each Pydantic model corresponds to a MongoDB collection. Collection name is the lowercase of the class name.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Core domain schemas

class Project(BaseModel):
    name: str
    tempo: int = Field(80, ge=40, le=200)
    key: str = Field("C minor")
    style: str = Field("Romantic", description="Romantic | Sad | One-sided")
    duration_sec: int = Field(120, ge=10, le=1200)
    instruments: List[str] = Field(default_factory=list)
    lyrics: Optional[str] = None
    assets: Dict[str, Any] = Field(default_factory=dict)
    owner_id: Optional[str] = None

class Track(BaseModel):
    project_id: str
    name: str
    kind: str = Field(..., description="instrument | vocal | fx")
    controls: Dict[str, float] = Field(default_factory=dict)
    muted: bool = False
    solo: bool = False
    asset_urls: Dict[str, str] = Field(default_factory=dict)  # stem, preview, midi

class VoiceProfile(BaseModel):
    name: str
    locale: str = Field("bn", description="bn | hi | en")
    gender: str = Field("female")
    preset: bool = False
    files: List[str] = Field(default_factory=list)
    quality_report: Dict[str, Any] = Field(default_factory=dict)
    demo_url: Optional[str] = None

class Job(BaseModel):
    type: str
    project_id: Optional[str] = None
    status: str = Field("queued", description="queued | running | done | error")
    progress: int = 0
    message: str = "Queued"
    logs: List[str] = Field(default_factory=list)
    result: Dict[str, Any] = Field(default_factory=dict)

class Asset(BaseModel):
    project_id: Optional[str] = None
    kind: str  # midi | wav | mp3 | video | image
    path: str
    url: str
    meta: Dict[str, Any] = Field(default_factory=dict)

# Auth
class User(BaseModel):
    email: str
    password_hash: str
    display_name: Optional[str] = None

# API payload schemas (request/response)
class GenerateInstrumentalRequest(BaseModel):
    projectId: str
    tempo: int
    key: str
    instruments: List[str]
    length_sec: int
    style: str

class GenerateMelodyRequest(BaseModel):
    projectId: str
    lyrics: str
    style: str
    tempo: int
    key: str

class SynthesizeVocalRequest(BaseModel):
    projectId: str
    voiceProfileId: str
    melodyUrl: str
    lyrics: str

class MixRequest(BaseModel):
    projectId: str
    stems: List[str]
    masterTargetLUFS: float = -14.0

class GenerateVideoRequest(BaseModel):
    projectId: str
    audioUrl: str
    style: str
    aspectRatio: str = Field("16:9")
