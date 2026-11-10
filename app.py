import os
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from uuid import UUID
from agent import ChatRequest, configured_engine

def create_app(engine=None):
    api = FastAPI(title='Care Navigation Console', version='1.0.0')
    engine = engine or configured_engine()
    api.state.engine = engine

    @api.get('/health')
    def health():
        return {'status': 'ok', 'provider': engine.provider.name, 'data': 'synthetic-only'}

    @api.post('/api/chat')
    async def chat(request: ChatRequest):
        return await engine.chat(request)

    @api.get('/api/traces')
    def traces(scope: UUID = Query(...)):
        return list(reversed([t for t in engine.traces if t['scope'] == str(scope)]))

    @api.get('/api/metrics')
    def metrics(scope: UUID = Query(...)):
        return engine.metrics(str(scope))

    web = Path(__file__).parent / 'web' / 'dist'
    if web.exists():
        api.mount('/', StaticFiles(directory=web, html=True), name='web')
    return api

app = create_app()
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', '8080')))
