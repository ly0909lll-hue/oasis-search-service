# Railway deployment configuration

Create two services in the same Railway project and production environment from this repository. Set both Root Directory values to `/`.

## Private SearXNG service

- Dockerfile path: `Dockerfile.searxng`
- Name: `searxng`
- Variables:
  - `SEARXNG_SECRET`: unique random secret, at least 32 characters
  - `SEARXNG_BIND_ADDRESS`: `0.0.0.0`
  - `SEARXNG_PORT`: `8080`
  - `SEARXNG_LIMITER`: `false`
  - `SEARXNG_PUBLIC_INSTANCE`: `false`
- Do not generate a public domain.

## Authenticated gateway

- Dockerfile path: `Dockerfile`
- Name: `gateway`
- Variables:
  - `OASIS_SEARCH_TOKEN`: a different unique random secret, at least 32 characters
  - `SEARXNG_UPSTREAM`: `http://searxng.railway.internal:8080/search`
  - `PORT`: `8080` if Railway has not supplied it
- Generate a public domain for this service only. Verify `/healthz` returns `{"status":"ok","provider":"searxng"}`.

## Connect OASIS

Set OASIS Site variables `SEARXNG_BASE_URL=https://<gateway-domain>` and `SEARXNG_API_KEY=<OASIS_SEARCH_TOKEN>` (mark the latter secret), then redeploy the saved Site version.
