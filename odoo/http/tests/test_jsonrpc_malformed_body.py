import json
import types
from typing import Any

import pytest
from werkzeug.exceptions import HTTPException

from odoo.http.dispatcher import JsonRPCDispatcher
from odoo.http.exceptions import ParameterError
from odoo.http.request_class import Request


def _dispatcher(body: bytes) -> JsonRPCDispatcher:
    httprequest: Any = types.SimpleNamespace(
        remote_addr=None, get_data=lambda: body, content_length=len(body)
    )
    request = Request(httprequest, app=None)
    request.db = None
    return JsonRPCDispatcher(request)


@pytest.mark.parametrize(
    ("body", "message", "request_id"),
    [
        (b"{not json", "Invalid JSON data", None),
        (b'"a string"', "Invalid JSON-RPC data", None),
        (
            b'{"jsonrpc": "2.0", "id": 7, "params": [1, 2]}',
            "params must be an object",
            7,
        ),
    ],
)
def test_every_malformed_body_answers_a_400_jsonrpc_envelope(body, message, request_id):
    dispatcher = _dispatcher(body)
    with pytest.raises(HTTPException) as caught:
        dispatcher.dispatch(types.SimpleNamespace(routing={}), {})

    response: Any = caught.value.response
    assert response is not None, "the error carries its own JSON body"
    assert response.status_code == 400
    assert response.headers["Content-Type"].startswith("application/json")
    envelope = json.loads(response.get_data())
    assert envelope["id"] == request_id, "the id is echoed once it is known"
    assert envelope["error"]["code"] == 400
    assert message in envelope["error"]["message"]


@pytest.mark.parametrize(
    "exc",
    [
        ParameterError("missing required parameter(s) ['db']"),
        ParameterError("parameter 'n' must be an integer"),
    ],
)
def test_a_parameter_error_answers_the_same_400_envelope_as_a_malformed_body(exc):
    dispatcher = _dispatcher(b'{"jsonrpc": "2.0", "id": 3, "params": {}}')
    dispatcher.request_id = 3

    response: Any = dispatcher.prepare_error_response(exc)

    assert response.status_code == 400
    envelope = json.loads(response.get_data())
    assert envelope == {
        "jsonrpc": "2.0",
        "id": 3,
        "error": {"code": 400, "message": exc.description, "data": {}},
    }


def test_a_handler_bad_request_keeps_the_handler_error_envelope():
    from werkzeug.exceptions import BadRequest

    dispatcher = _dispatcher(b"{}")
    response: Any = dispatcher.prepare_error_response(BadRequest("from a handler"))
    assert response.status_code == 200
    assert json.loads(response.get_data())["error"]["code"] == 0
