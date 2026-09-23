import http.client
import json
import os
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault("OASIS_SEARCH_TOKEN", "test-token-that-is-at-least-32-characters-long")
import gateway


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit=-1):
        return self.body[:limit]


class GatewayQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = gateway.ThreadingHTTPServer(("127.0.0.1", 0), gateway.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def post(self, path, body, token=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        connection.request("POST", path, body=json.dumps(body), headers=headers)
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_rejects_unauthorized_request(self):
        status, body = self.post("/v1/chat/completions", {"messages": []})
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "unauthorized")

    def test_reports_missing_openai_secret(self):
        with patch.object(gateway, "OPENAI_API_KEY", ""):
            status, body = self.post("/v1/chat/completions", {"messages": []}, gateway.TOKEN)
        self.assertEqual(status, 503)
        self.assertIn("not configured", body["error"])

    def test_forwards_authenticated_request_with_server_model_and_secret(self):
        captured = {}
        def fake_open(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["body"] = json.loads(request.data)
            captured["timeout"] = timeout
            return FakeResponse(json.dumps({"choices": [{"message": {"content": "{}"}}]}).encode())

        payload = {"model": "client-selected-model", "messages": [{"role": "user", "content": "test"}]}
        with patch.object(gateway, "OPENAI_API_KEY", "server-only-test-key"), \
             patch.object(gateway, "OPENAI_MODEL", "gpt-4.1-mini"), \
             patch.object(gateway.urllib.request, "urlopen", side_effect=fake_open):
            status, body = self.post("/v1/chat/completions", payload, gateway.TOKEN)

        self.assertEqual(status, 200)
        self.assertIn("choices", body)
        self.assertEqual(captured["url"], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(captured["authorization"], "Bearer server-only-test-key")
        self.assertEqual(captured["body"]["model"], "gpt-4.1-mini")
        self.assertEqual(captured["timeout"], 35)


if __name__ == "__main__":
    unittest.main()
