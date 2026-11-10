# Care Navigation Console

A full-stack engineering work sample for a synthetic care-navigation agent: a React/TypeScript interface, Python/FastAPI services, a bounded directory lookup tool, and an optional Gemini structured-output router. The focus is request routing, latency visibility, failure handling, and reducing unnecessary model calls.

This is an independent portfolio prototype. All requests and resources must be fictional. It is not affiliated with a healthcare provider, does not deliver care, and has no clinical validation or HIPAA compliance claim.

## Run locally

Use Python 3.11+ and Node.js 22.12+.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cd web
npm ci
npm run build
cd ..
python app.py
```

Open http://localhost:8080. The default fixture provider runs entirely offline. Select an example, send it, then repeat it to see a cache hit. The browser keeps a random scope for its current page session. No request text is written to traces.

```sh
python -m unittest discover -s tests -v
python benchmark.py --check
```

## Implementation

- **Frontend:** React and strict TypeScript; editable fictional requests, loading/error states, keyboard-accessible controls, resource cards, a session metrics panel, and execution traces.
- **API:** FastAPI and Pydantic validate the synthetic-only flag, random UUID scope, bounded input, and closed output categories. `/health`, `/api/chat`, `/api/metrics`, and `/api/traces` are documented at `/docs`.
- **Orchestration:** an explicit logistical route can skip the model. Ambiguous requests use a structured router, followed by a deterministic lookup in a fictional resource directory. The model cannot choose arbitrary URLs or execute commands. Responses use fixed templates; medical and unknown requests hand off to a human.
- **Optimization:** session-scoped, model-versioned TTL cache with a 256-entry bound; duplicate in-flight request coalescing; a four-call concurrency semaphore; compact routing-only prompts and capped output. No conversation history is sent. These are code-level controls, not a measured cloud-spend reduction.
- **Reliability:** a nine-second engine timeout, one retry on selected temporary HTTP errors, closed-schema model output, human fallback, and no cached failures. Bounded traces include stages, route, latency, token-source labels, and failure type. Structured logs omit raw messages.
- **Usage:** fixture token estimates and Gemini-reported input/output tokens are separated. Cached and coalesced requests do not count the same successful model response twice. Failed attempts can still incur provider charges, so these counters are not billing reconciliation.
- **Delivery:** GitHub Actions runs backend tests, the offline regression check, TypeScript checking, and the frontend production build. A non-root multi-stage Dockerfile packages both layers; `PORT` and `0.0.0.0` binding follow the Cloud Run container contract.

## Measured offline result

`benchmark-results.json` records an eight-request fixture set repeated three times. Both baseline and optimized variants returned the expected route on **24/24 requests**. Explicit routing and caching reduced fixture model calls **from 24 to 4 (83.33%)**. Four additional edge cases test medical handoff, instruction overrides, ambiguity, and multi-category requests. These cases and the fixture classifier are deliberately small and transparent; this is a regression test, not evidence of clinical safety, live model accuracy, or real-world cost savings. The simulated provider delay makes latency figures unsuitable as live-model performance claims; p95 did not materially improve in this run.

Ten tests cover API validation, scoped cache isolation and capacity, TTL expiration, concurrent duplicate requests, token deduplication, timeout fallback, raw-text omission, mocked Gemini retry/usage, and invalid structured responses.

## Optional Gemini adapter

Set `PROVIDER=gemini`, `GEMINI_MODEL` to a currently supported model ID, and `GEMINI_API_KEY` in your local environment. Never commit credentials. Keep the key on the backend and use fictional inputs only. The adapter uses `generateContent` with `responseJsonSchema` and reads `usageMetadata`; its request/response behavior is verified using `httpx.MockTransport`. **No live Gemini call was performed for this work sample.** See the [official Gemini API reference](https://ai.google.dev/api/generate-content).

## Optional Google Cloud deployment

The Dockerfile and the example below are deployment preparation. The image was not built or deployed to Google Cloud in this work sample. Use a dedicated demo GCP project with authenticated access; do not expose this no-auth prototype as a patient service.

```sh
gcloud run deploy care-navigation-console \
  --source . \
  --region us-east1 \
  --no-allow-unauthenticated \
  --concurrency 4 \
  --max-instances 1 \
  --memory 512Mi \
  --set-env-vars PROVIDER=fixture
```

The [Cloud Run container contract](https://docs.cloud.google.com/run/docs/container-contract) explains the runtime binding. This configuration is illustrative, not validated infrastructure-as-code.

## Boundaries and tradeoffs

The per-process cache and traces are temporary and do not coordinate across replicas. A random scope is a demo grouping key, not authentication or authorization. The trace store holds the last 500 requests globally. The router is lexical/LLM-based and is not a safety classifier; negation and complex requests can be misunderstood. Production work would require proper identity, tenant authorization, data retention controls, encrypted/shared state, robust monitoring, clinical review, adversarial evaluation, and applicable privacy controls. None of those are claimed here. Do not enter patient information.
