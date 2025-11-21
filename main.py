import os
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import db, create_document
from schemas import (
    Project, Track, VoiceProfile, Job,
    GenerateInstrumentalRequest, GenerateMelodyRequest,
    SynthesizeVocalRequest, MixRequest, GenerateVideoRequest
)
from bson import ObjectId
import wave
import contextlib

ASSETS_DIR = os.path.join(os.getcwd(), 'assets')
os.makedirs(ASSETS_DIR, exist_ok=True)

app = FastAPI(title="AI Song Generator (Reference)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# ---------- Helpers ----------

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")


def save_wav_silence(path: str, duration_sec: float = 2.0, samplerate: int = 44100):
    frames = int(duration_sec * samplerate)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        silence = (b"\x00\x00") * frames
        wf.writeframes(silence)


def job_create(job_type: str, project_id: Optional[str] = None, message: str = "Queued") -> str:
    job_doc = Job(type=job_type, project_id=project_id, message=message).model_dump()
    job_id = create_document('job', job_doc)
    return job_id


def job_update(job_id: str, **fields):
    db['job'].update_one({'_id': oid(job_id)}, {'$set': fields})


def job_append_log(job_id: str, msg: str):
    db['job'].update_one({'_id': oid(job_id)}, {'$push': {'logs': f"{datetime.utcnow().isoformat()} - {msg}"}})


def asset_create(kind: str, file_path: str, project_id: Optional[str] = None, meta: Dict[str, Any] = None) -> Dict[str, Any]:
    url = f"/assets/{os.path.basename(file_path)}"
    asset = {
        'project_id': project_id,
        'kind': kind,
        'path': file_path,
        'url': url,
        'meta': meta or {},
        'created_at': datetime.utcnow()
    }
    _id = db['asset'].insert_one(asset).inserted_id
    asset['id'] = str(_id)
    return asset


# ---------- Basic routes ----------

@app.get("/")
async def root():
    return {"name": "AI Song Generator", "status": "ok"}


class CreateProjectBody(BaseModel):
    name: str
    tempo: int = 80
    key: str = "C minor"
    style: str = "Romantic"
    duration_sec: int = 120
    instruments: List[str] = []
    lyrics: Optional[str] = None


@app.post("/api/projects")
async def create_project(body: CreateProjectBody):
    proj = Project(**body.model_dump())
    pid = create_document('project', proj)
    return {"projectId": pid}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    doc = db['project'].find_one({'_id': oid(project_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc['id'] = str(doc['_id'])
    doc.pop('_id', None)
    return doc


# ---------- Generation endpoints (mock-mode) ----------

@app.post("/api/generate/melody")
async def generate_melody(req: GenerateMelodyRequest):
    job_id = job_create('melody', req.projectId, message="Generating melody from lyrics...")
    asyncio.create_task(_worker_melody(job_id, req))
    return {"jobId": job_id, "status": "queued"}


async def _worker_melody(job_id: str, req: GenerateMelodyRequest):
    try:
        job_update(job_id, status='running', progress=5, message='Analyzing lyrics and style')
        job_append_log(job_id, 'Parsing lyrics and estimating syllable counts')
        await asyncio.sleep(0.5)

        # Create dummy MIDI (text placeholder) and guide WAV
        midi_name = f"melody_{uuid.uuid4().hex}.mid.txt"
        midi_path = os.path.join(ASSETS_DIR, midi_name)
        with open(midi_path, 'w') as f:
            f.write(f"MIDI_PLACEHOLDER tempo={req.tempo} key={req.key} style={req.style}\n")
            for i, line in enumerate(req.lyrics.splitlines()):
                if line.strip():
                    f.write(f"t={i*2.0:.2f}s lyric={line.strip()} note=C4 len=1.0\n")
        job_update(job_id, progress=40, message='Draft melody created')
        job_append_log(job_id, f'Melody file: {midi_name}')

        guide_name = f"guide_{uuid.uuid4().hex}.wav"
        guide_path = os.path.join(ASSETS_DIR, guide_name)
        save_wav_silence(guide_path, duration_sec=max(4.0, min(60.0, req.tempo/10)))
        job_update(job_id, progress=75, message='Rendering guide audio')

        midi_asset = asset_create('midi', midi_path, req.projectId, meta={'tempo': req.tempo, 'key': req.key})
        guide_asset = asset_create('wav', guide_path, req.projectId)

        mapping = []
        t = 0.0
        for line in req.lyrics.splitlines():
            if line.strip():
                mapping.append({'start': round(t,2), 'end': round(t+2.0,2), 'text': line.strip()})
                t += 2.0
        result = {"midiUrl": midi_asset['url'], "guideUrl": guide_asset['url'], "lyricTimestamps": mapping}
        job_update(job_id, status='done', progress=100, message='Melody ready', result=result)
    except Exception as e:
        job_update(job_id, status='error', message=str(e))


@app.post("/api/generate/instrumental")
async def generate_instrumental(req: GenerateInstrumentalRequest):
    job_id = job_create('instrumental', req.projectId, message="Generating instrumental stems...")
    asyncio.create_task(_worker_instrumental(job_id, req))
    return {"jobId": job_id, "status": "queued"}


async def _worker_instrumental(job_id: str, req: GenerateInstrumentalRequest):
    try:
        job_update(job_id, status='running', progress=10, message='Preparing stems')
        await asyncio.sleep(0.5)
        stems = []
        per = 70/max(1, len(req.instruments))
        for i, inst in enumerate(req.instruments):
            nm = f"stem_{inst.lower()}_{uuid.uuid4().hex}.wav"
            pth = os.path.join(ASSETS_DIR, nm)
            save_wav_silence(pth, duration_sec=min(30, req.length_sec))
            asset = asset_create('wav', pth, req.projectId, meta={'instrument': inst})
            stems.append(asset['url'])
            job_update(job_id, progress=min(90, int(10+per*(i+1))), message=f'{inst} generated')
        result = {"stems": stems}
        job_update(job_id, status='done', progress=100, message='Instrumental stems ready', result=result)
    except Exception as e:
        job_update(job_id, status='error', message=str(e))


@app.post("/api/upload/voice")
async def upload_voice(files: List[UploadFile] = File(...), name: str = Form("Custom Voice"), locale: str = Form("bn"), gender: str = Form("female")):
    if len(files) < 1:
        raise HTTPException(status_code=400, detail="Upload at least 1 file")
    saved = []
    report: Dict[str, Any] = {"clips": []}
    for f in files[:30]:
        if not f.filename.lower().endswith('.wav'):
            raise HTTPException(status_code=400, detail="Only WAV files allowed")
        data = await f.read()
        if len(data) > 10*1024*1024:
            raise HTTPException(status_code=400, detail="Clip exceeds 10MB")
        fname = f"voice_{uuid.uuid4().hex}.wav"
        fpath = os.path.join(ASSETS_DIR, fname)
        with open(fpath, 'wb') as out:
            out.write(data)
        # basic checks
        try:
            with contextlib.closing(wave.open(fpath, 'rb')) as wf:
                channels = wf.getnchannels()
                sr = wf.getframerate()
                frames = wf.getnframes()
                dur = frames/float(sr)
        except Exception:
            channels, sr, dur = 0, 0, 0
        clip_report = {
            'file': f"/assets/{fname}", 'channels': channels, 'sample_rate': sr,
            'duration_sec': round(dur,2), 'mono_ok': channels == 1,
            'sr_ok': 16000 <= sr <= 48000,
        }
        report['clips'].append(clip_report)
        saved.append(f"/assets/{fname}")
    quality_ok = all(c['mono_ok'] and c['sr_ok'] and c['duration_sec'] >= 0.3 for c in report['clips'])
    report['quality_ok'] = quality_ok
    profile = VoiceProfile(name=name, locale=locale, gender=gender, files=saved, quality_report=report, preset=False).model_dump()
    vid = db['voiceprofile'].insert_one(profile).inserted_id
    demo_name = f"voice_demo_{uuid.uuid4().hex}.wav"
    demo_path = os.path.join(ASSETS_DIR, demo_name)
    save_wav_silence(demo_path, duration_sec=2)
    demo_url = f"/assets/{demo_name}"
    db['voiceprofile'].update_one({'_id': vid}, {'$set': {'demo_url': demo_url}})
    return {"voiceProfileId": str(vid), "quality": report, "demoUrl": demo_url}


@app.delete("/api/voice/{voice_id}")
async def delete_voice(voice_id: str):
    res = db['voiceprofile'].delete_one({'_id': oid(voice_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


@app.post("/api/synthesize/vocal")
async def synthesize_vocal(req: SynthesizeVocalRequest):
    job_id = job_create('vocal', req.projectId, message='Synthesizing vocals')
    asyncio.create_task(_worker_vocal(job_id, req))
    return {"jobId": job_id}


async def _worker_vocal(job_id: str, req: SynthesizeVocalRequest):
    try:
        job_update(job_id, status='running', progress=20, message='Adapting voice')
        await asyncio.sleep(0.5)
        takes = []
        for i in range(2):
            nm = f"vocal_take{i+1}_{uuid.uuid4().hex}.wav"
            pth = os.path.join(ASSETS_DIR, nm)
            save_wav_silence(pth, duration_sec=6)
            takes.append(f"/assets/{nm}")
        job_update(job_id, status='done', progress=100, message='Vocals ready', result={'takes': takes})
    except Exception as e:
        job_update(job_id, status='error', message=str(e))


@app.post("/api/mix")
async def mix(req: MixRequest):
    job_id = job_create('mix', req.projectId, message='Mixing and mastering to -14 LUFS')
    asyncio.create_task(_worker_mix(job_id, req))
    return {"jobId": job_id}


async def _worker_mix(job_id: str, req: MixRequest):
    try:
        job_update(job_id, status='running', progress=30, message='Balancing tracks')
        await asyncio.sleep(0.5)
        master_nm = f"master_{uuid.uuid4().hex}.wav"
        master_path = os.path.join(ASSETS_DIR, master_nm)
        save_wav_silence(master_path, duration_sec=10)
        master_asset = asset_create('wav', master_path, req.projectId, meta={'lufs': req.masterTargetLUFS})
        job_update(job_id, status='done', progress=100, message='Master ready', result={'masterUrl': master_asset['url']})
    except Exception as e:
        job_update(job_id, status='error', message=str(e))


@app.post("/api/generate/video")
async def generate_video(req: GenerateVideoRequest):
    job_id = job_create('video', req.projectId, message='Generating video with subtitles')
    asyncio.create_task(_worker_video(job_id, req))
    return {"jobId": job_id}


async def _worker_video(job_id: str, req: GenerateVideoRequest):
    try:
        job_update(job_id, status='running', progress=25, message='Compositing scenes')
        await asyncio.sleep(0.5)
        # thumbnails
        thumbs = []
        for i in range(4):
            name = f"thumb_{uuid.uuid4().hex}.png"
            path = os.path.join(ASSETS_DIR, name)
            with open(path, 'wb') as f:
                f.write(os.urandom(128))
            thumbs.append(f"/assets/{name}")
        vid_name = f"video_{uuid.uuid4().hex}.mp4"
        vid_path = os.path.join(ASSETS_DIR, vid_name)
        # placeholder mp4 (not a real mp4, but a stub file for demo)
        with open(vid_path, 'wb') as f:
            f.write(os.urandom(2048))
        video_asset = asset_create('video', vid_path, req.projectId, meta={'aspectRatio': req.aspectRatio})
        job_update(job_id, status='done', progress=100, message='Video ready', result={'videoUrl': video_asset['url'], 'thumbnails': thumbs})
    except Exception as e:
        job_update(job_id, status='error', message=str(e))


@app.get("/api/job/{job_id}/status")
async def job_status(job_id: str):
    j = db['job'].find_one({'_id': oid(job_id)})
    if not j:
        raise HTTPException(status_code=404, detail='Job not found')
    j['id'] = str(j['_id'])
    j.pop('_id', None)
    return j


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, 'name', '✅ Connected')
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
