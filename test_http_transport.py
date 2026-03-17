import hashlib
import importlib
import os

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "dummy_hash")

main = importlib.import_module("main")


def _md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


def test_http_session_md5_prefers_session_string(monkeypatch):
    monkeypatch.setattr(main, "SESSION_STRING", "string-session")
    monkeypatch.setattr(main, "TELEGRAM_SESSION_NAME", "file-session")

    assert main._get_http_session_md5() == _md5("string-session")


def test_http_session_query_authorization_requires_matching_md5(monkeypatch):
    monkeypatch.setattr(main, "SESSION_STRING", None)
    monkeypatch.setattr(main, "TELEGRAM_SESSION_NAME", "file-session")

    expected = main._get_http_session_md5()

    assert expected is not None
    assert not main._is_http_session_query_authorized(b"")
    assert not main._is_http_session_query_authorized(b"session_md5=wrong")
    assert main._is_http_session_query_authorized(f"session_md5={expected}".encode())


def test_streamable_http_app_rejects_requests_without_matching_md5(monkeypatch):
    monkeypatch.setattr(main, "SESSION_STRING", None)
    monkeypatch.setattr(main, "TELEGRAM_SESSION_NAME", "file-session")

    async def ok(_request):
        return PlainTextResponse("ok")

    fake_streamable_app = Starlette(routes=[Route("/mcp", ok)])
    monkeypatch.setattr(main.mcp, "streamable_http_app", lambda: fake_streamable_app)

    expected = main._get_http_session_md5()

    with TestClient(main._build_streamable_http_app()) as client:
        assert client.get("/mcp").status_code == 403
        assert client.get(f"/mcp?session_md5={expected}").text == "ok"
