import json
import types
from typing import Any

import pytest
from werkzeug.exceptions import HTTPException

from odoo.http._response import _RequestResponseMixin
from odoo.http.dispatcher import JsonRPCDispatcher


def _dispatcher(body: bytes) -> JsonRPCDispatcher:
    request: Any = types.SimpleNamespace(
        httprequest=types.SimpleNamespace(
            get_data=lambda: body, content_length=len(body)
        ),
        params={},
        db=None,
        registry=None,
        prepare_json_response=None,
        prepare_response=None,
    )
    request.get_json_data = lambda: json.loads(body)
    request.prepare_response = _RequestResponseMixin.prepare_response.__get__(request)
    request.prepare_json_response = _RequestResponseMixin.prepare_json_response.__get__(
        request
    )
    return JsonRPCDispatcher(request)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"{not json", "Invalid JSON data"),
        (b'"a string"', "Invalid JSON-RPC data"),
        (b'{"jsonrpc": "2.0", "id": 7, "params": [1, 2]}', "params must be an object"),
    ],
)
def test_every_malformed_body_answers_a_400_jsonrpc_envelope(body, message):
    dispatcher = _dispatcher(body)
    with pytest.raises(HTTPException) as caught:
        dispatcher.dispatch(types.SimpleNamespace(routing={}), {})

    response: Any = caught.value.response
    assert response is not None, "the error carries its own JSON body"
    assert response.status_code == 400
    assert response.headers["Content-Type"].startswith("application/json")
    error = json.loads(response.get_data())["error"]
    assert error["code"] == 400
    assert message in error["message"]
