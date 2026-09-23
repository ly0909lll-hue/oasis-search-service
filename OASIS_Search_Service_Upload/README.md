# OASIS Search Service

This repository contains the standalone SearXNG service and an authenticated JSON gateway.

The gateway can also relay OASIS AI qualification requests to OpenAI. Add `OPENAI_API_KEY` as a Railway Secret on the `oasis-search-gateway` service. Optionally set `QUALIFICATION_MODEL` (defaults to `gpt-4.1-mini`). The OpenAI key is only used by the gateway and must not be added to source control or the OASIS browser app.

For Railway, create two services from this same repository, both with the repository root as the root directory:

- `searxng`: Dockerfile path `Dockerfile.searxng`; keep private and do not generate a public domain.
- `gateway`: Dockerfile path `Dockerfile`; generate the public HTTPS domain for this service only.

Configure Railway variables as described in the separate deployment guide delivered with this package. Never commit real secrets.
