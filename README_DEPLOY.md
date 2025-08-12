# Deploy na nuvem — Mini Eklipse

## Passos rápidos (Railway)
1. Suba seu projeto no GitHub (com `Dockerfile` e pastas).
2. Railway → New Project → Deploy from GitHub → selecione o repo.
3. Aguarde o build e abra a URL pública.

## Passos (Render)
1. Render → New → Web Service → selecione o repo.
2. Ambiente: Docker (usa seu Dockerfile).
3. Deploy e teste a URL.

Arquivos necessários no repo:
- app.py, processor.py, main.py, render_916.py, fortnite_preset.json
- requirements.txt, requirements_site.txt
- templates/
- Dockerfile, .dockerignore
