import types

from odoo.http._cors import is_cors_preflight


def _fake_request(method):
    env = {"REQUEST_METHOD": method}
    httprequest = types.SimpleNamespace(method=method, environ=env)
    return types.SimpleNamespace(httprequest=httprequest)


def test_is_cors_preflight_returns_real_bool():
    endpoint = types.SimpleNamespace(routing={"cors": "https://example.com"})
    result = is_cors_preflight(_fake_request("OPTIONS"), endpoint)
    assert result is True
    assert is_cors_preflight(_fake_request("GET"), endpoint) is False
    no_cors = types.SimpleNamespace(routing={})
    assert is_cors_preflight(_fake_request("OPTIONS"), no_cors) is False
