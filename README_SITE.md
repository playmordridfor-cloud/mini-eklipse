# Site MVP - Mini Eklipse (local)

Este é um MVP de site local com **FastAPI** que recebe o link do VOD da Twitch,
roda seus scripts (`main.py` e `render_916.py`) em background e entrega o compilado + clipes 9:16.

## Pré-requisitos
- Estar na mesma pasta onde estão `main.py`, `render_916.py`, `fortnite_preset.json`.
- Ter instalado as libs do seu projeto (librosa, yt-dlp, etc.).
- Instalar dependências do site:
```
pip install -r requirements_site.txt
```

## Como rodar
```
uvicorn app:app --reload
```
Abra no navegador: http://127.0.0.1:8000/

Cole o link do VOD e acompanhe o status em `/status/<job_id>`.
Os arquivos ficam em `jobs/<job_id>/`.
