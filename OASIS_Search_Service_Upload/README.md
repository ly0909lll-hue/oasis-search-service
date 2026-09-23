# OASIS Search Service

This repository contains the standalone SearXNG service and an authenticated JSON gateway.

For Railway, create two services from this same repository, both with the repository root as the root directory:

- `searxng`: Dockerfile path `Dockerfile.searxng`; keep private and do not generate a public domain.
- `gateway`: Dockerfile path `Dockerfile`; generate the public HTTPS domain for this service only.

Configure Railway variables as described in the separate deployment guide delivered with this package. Never commit real secrets.
