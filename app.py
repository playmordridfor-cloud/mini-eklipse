from fastapi import FastAPI, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uuid, os
from processor import process_vod

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/jobs', StaticFiles(directory='jobs'), name='jobs')
templates = Jinja2Templates(directory='templates')

@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.post('/jobs', response_class=HTMLResponse)
def create_job(request: Request, background_tasks: BackgroundTasks, vod_url: str = Form(...)):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join('jobs', job_id)
    os.makedirs(job_dir, exist_ok=True)
    # mark pending
    with open(os.path.join(job_dir, 'status.json'), 'w', encoding='utf-8') as f:
        f.write('{"status":"pending"}')
    # spawn background processing
    background_tasks.add_task(process_vod, job_id, vod_url)
    return RedirectResponse(url=f'/status/{job_id}', status_code=303)

@app.get('/status/{job_id}', response_class=HTMLResponse)
def status(request: Request, job_id: str):
    job_dir = os.path.join('jobs', job_id)
    status_path = os.path.join(job_dir, 'status.json')
    if not os.path.exists(status_path):
        return HTMLResponse('<h1>Job não encontrado</h1>', status_code=404)
    with open(status_path, 'r', encoding='utf-8') as f:
        data = f.read()
    try:
        st = __import__('json').loads(data)
    except Exception:
        st = {'status':'unknown'}

    return templates.TemplateResponse('status.html', {
        'request': request,
        'job_id': job_id,
        'status': st.get('status','unknown'),
        'message': st.get('message',''),
        'compiled': st.get('compiled'),
        'clips_zip': st.get('clips_zip'),
        'clip_samples': st.get('clip_samples', []),
    })
