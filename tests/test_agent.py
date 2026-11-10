import asyncio
import json
import unittest
from uuid import uuid4
import httpx
from fastapi.testclient import TestClient
from agent import ChatRequest, Engine, GeminiProvider
from app import create_app

class AgentTests(unittest.IsolatedAsyncioTestCase):
    def req(self, text='I need help getting there.', scope=None):
        return ChatRequest(scope=scope or uuid4(), message=text, synthetic=True)

    async def test_cache_and_token_accounting(self):
        engine=Engine(); req=self.req()
        first=await engine.chat(req); second=await engine.chat(req)
        self.assertEqual(first['trace']['route'], 'model')
        self.assertEqual(second['trace']['route'], 'cache')
        self.assertEqual(engine.provider.calls,1)
        self.assertEqual(engine.metrics(str(req.scope))['tokens']['fixture_estimate']['input'],first['trace']['input_tokens'])

    async def test_cache_scope_and_bound(self):
        engine=Engine(capacity=1)
        await engine.chat(self.req()); await engine.chat(self.req())
        self.assertEqual(engine.provider.calls,2)
        self.assertEqual(len(engine.cache),1)

    async def test_expired_cache(self):
        engine=Engine(ttl=-1); req=self.req()
        await engine.chat(req); await engine.chat(req)
        self.assertEqual(engine.provider.calls,2)

    async def test_coalescing(self):
        engine=Engine(); req=self.req()
        replies=await asyncio.gather(*(engine.chat(req) for _ in range(8)))
        self.assertEqual(engine.provider.calls,1)
        self.assertEqual(sum(r['trace']['route']=='coalesced' for r in replies),7)
        self.assertEqual(sum(r['trace']['input_tokens']>0 for r in replies),1)

    async def test_timeout_handoff_not_cached(self):
        engine=Engine(timeout=.001)
        reply=await engine.chat(self.req())
        self.assertEqual(reply['trace']['route'],'fallback')
        self.assertEqual(reply['resource']['id'],'demo-navigator')
        self.assertEqual(len(engine.cache),0)

    async def test_rules_and_medical_handoff(self):
        engine=Engine()
        appointment=await engine.chat(self.req('Can I arrange an appointment?'))
        medical=await engine.chat(self.req('What dose is right for treatment?'))
        self.assertEqual(appointment['trace']['category'],'appointments')
        self.assertEqual(medical['trace']['category'],'human')
        self.assertEqual(engine.provider.calls,0)

    async def test_traces_omit_raw_text(self):
        engine=Engine(); req=self.req('A fictional unique message for transport')
        await engine.chat(req)
        self.assertNotIn(req.message,json.dumps(list(engine.traces)))

    async def test_retry_and_reported_usage(self):
        attempts=[]
        def handler(request):
            attempts.append(request)
            if len(attempts)==1:return httpx.Response(503)
            return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'{"category":"transport"}'}]}}],'usageMetadata':{'promptTokenCount':42,'candidatesTokenCount':7}})
        provider=GeminiProvider('fake','test-model',httpx.MockTransport(handler))
        reply=await provider.classify('fictional ride')
        self.assertEqual(provider.calls,2)
        self.assertEqual(reply.input_tokens,42)
        self.assertEqual(reply.token_source,'provider_reported')
        self.assertIn('responseJsonSchema',json.loads(attempts[1].content)['generationConfig'])

    async def test_bad_output_fails_closed(self):
        def handler(request):
            return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'{"category":"prescribe"}'}]}}]})
        provider=GeminiProvider('fake','test-model',httpx.MockTransport(handler))
        reply=await Engine(provider).chat(self.req())
        self.assertEqual(reply['trace']['route'],'fallback')
        self.assertEqual(reply['trace']['category'],'human')
        self.assertEqual(provider.calls,1)

class ApiTests(unittest.TestCase):
    def test_api_validation_and_scoping(self):
        with TestClient(create_app(Engine())) as client:
            self.assertEqual(client.get('/health').status_code,200)
            scope=str(uuid4()); body={'scope':scope,'message':'Help with an appointment','synthetic':True}
            response=client.post('/api/chat',json=body)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['resource']['id'],'demo-appointments')
            self.assertEqual(client.get('/api/metrics',params={'scope':scope}).json()['requests'],1)
            self.assertEqual(client.get('/api/traces',params={'scope':str(uuid4())}).json(),[])
            self.assertEqual(client.post('/api/chat',json={**body,'synthetic':False}).status_code,422)
            self.assertEqual(client.post('/api/chat',json={**body,'message':'x'*601}).status_code,422)
            self.assertEqual(client.get('/api/traces').status_code,422)
