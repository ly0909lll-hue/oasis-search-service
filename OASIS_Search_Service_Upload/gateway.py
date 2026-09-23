import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("OASIS_SEARCH_TOKEN", "")
UPSTREAM = os.environ.get("SEARXNG_UPSTREAM", "http://searxng:8080/search")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("QUALIFICATION_MODEL", "gpt-4.1-mini")
OPENAI_CHAT_COMPLETIONS = "https://api.openai.com/v1/chat/completions"
if len(TOKEN) < 32:
    raise RuntimeError("OASIS_SEARCH_TOKEN must be at least 32 characters")


class Handler(BaseHTTPRequestHandler):
    server_version = "OASIS-Search-Gateway/1.0"
    def log_message(self, fmt, *args):
        # Search terms are business data: never write them to routine logs.
        print("%s %s" % (self.client_address[0], args[1] if len(args) > 1 else "request"), flush=True)

    def send_json(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        auth = self.headers.get("Authorization", "")
        supplied = auth[7:] if auth.startswith("Bearer ") else ""
        return hmac.compare_digest(supplied.encode(), TOKEN.encode())

    def do_GET(self):
        if self.path == "/healthz":
            self.send_json(200, {"status": "ok", "provider": "searxng"})
            return
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/search":
            self.send_json(404, {"error": "not found"})
            return
        if not self.authorized():
            self.send_json(401, {"error": "unauthorized"})
            return
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        query = params.get("q", [""])[0].strip()
        if not query or len(query) > 500:
            self.send_json(400, {"error": "q must contain 1 to 500 characters"})
            return
        language = params.get("language", ["en"])[0]
        if not (language == "en" or language == "ar" or len(language) == 5 and language[2] == "-"):
            language = "en"
        outgoing = urllib.parse.urlencode({"q": query, "format": "json", "categories": "general", "language": language, "safesearch": "1"})
        request = urllib.request.Request(UPSTREAM + "?" + outgoing, headers={"Accept": "application/json", "User-Agent": "OASIS-Search-Gateway/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=22) as response:
                data = response.read(2_000_001)
                if len(data) > 2_000_000:
                    self.send_json(502, {"error": "upstream response too large"})
                    return
                parsed_data = json.loads(data)
                if not isinstance(parsed_data, dict) or not isinstance(parsed_data.get("results"), list):
                    self.send_json(502, {"error": "invalid SearXNG response"})
                    return
                self.send_response(response.status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as error:
            self.send_json(error.code if error.code in (429, 503) else 502, {"error": "SearXNG upstream unavailable"})
        except Exception:
            self.send_json(502, {"error": "SearXNG upstream unavailable"})

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/v1/chat/completions":
            self.send_json(404, {"error": "not found"})
            return
        if not self.authorized():
            self.send_json(401, {"error": "unauthorized"})
            return
        if not OPENAI_API_KEY:
            self.send_json(503, {"error": "AI qualification is not configured on this service"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "invalid content length"})
            return
        if length < 1 or length > 128_000:
            self.send_json(413 if length > 128_000 else 400, {"error": "request body must be 1 to 128000 bytes"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "invalid JSON body"})
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
            self.send_json(400, {"error": "messages must be an array"})
            return
        # Keep model selection server-side so callers cannot use the gateway to
        # invoke a more expensive model than the one configured for OASIS.
        payload["model"] = OPENAI_MODEL
        request = urllib.request.Request(
            OPENAI_CHAT_COMPLETIONS,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": "Bearer " + OPENAI_API_KEY,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "OASIS-AI-Qualification-Gateway/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                data = response.read(1_000_001)
                if len(data) > 1_000_000:
                    self.send_json(502, {"error": "AI provider response too large"})
                    return
                parsed_data = json.loads(data)
                if not isinstance(parsed_data, dict):
                    self.send_json(502, {"error": "invalid AI provider response"})
                    return
                self.send_json(response.status, parsed_data)
        except urllib.error.HTTPError as error:
            # Preserve actionable status codes while never returning provider
            # response bodies that could contain sensitive request details.
            status = error.code if error.code in (400, 401, 403, 429) else 502
            self.send_json(status, {"error": "AI provider request failed"})
        except Exception:
            self.send_json(502, {"error": "AI provider unavailable"})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
