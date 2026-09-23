from unittest import mock

import werkzeug.exceptions

from odoo.http import dispatcher
from odoo.http.dispatcher import is_debugger_handover_required

_BUG = RuntimeError("boom")


def _dispatcher(serializes: bool):
    return mock.Mock(serializes_errors_in_dev_mode=serializes)


def test_no_handover_without_an_attached_debugger():
    assert dispatcher.debugger_attached is False, (
        "importing odoo.http must not attach a debugger"
    )
    assert is_debugger_handover_required(None, _BUG) is False


def test_handover_once_a_debugger_is_attached():
    with mock.patch.object(dispatcher, "debugger_attached", True):
        assert is_debugger_handover_required(None, _BUG) is True


def test_a_serialising_dispatcher_is_exempt():
    with mock.patch.object(dispatcher, "debugger_attached", True):
        assert is_debugger_handover_required(_dispatcher(True), _BUG) is False
        assert is_debugger_handover_required(_dispatcher(False), _BUG) is True


def test_an_http_answer_is_never_a_debugger_case():
    html = _dispatcher(False)
    with mock.patch.object(dispatcher, "debugger_attached", True):
        for answer in (
            werkzeug.exceptions.NotFound(),
            werkzeug.exceptions.Forbidden(),
            werkzeug.exceptions.BadRequest(),
        ):
            assert is_debugger_handover_required(html, answer) is False
        assert is_debugger_handover_required(
            html, werkzeug.exceptions.InternalServerError()
        )
        assert is_debugger_handover_required(
            html, werkzeug.exceptions.HTTPException()
        ), "a status-less exception is a defect, not an answer"


def test_the_serving_tier_and_the_entry_point_ask_one_question():
    from odoo.http import _serve, application

    assert _serve.is_debugger_handover_required is is_debugger_handover_required
    assert application.is_debugger_handover_required is is_debugger_handover_required


def test_dev_mode_without_an_attached_debugger_still_renders_through_ir_http():
    from odoo.http import settings as http_settings
    from odoo.http._serve import _RequestServeMixin

    served = _RequestServeMixin()
    served.dispatcher = _dispatcher(False)
    served.registry = mock.Mock()
    handled = []

    def handle_error(exc):
        handled.append(exc)
        return "rendered"

    ir_http = mock.Mock(_handle_error=handle_error)
    with (
        http_settings.override(dev_mode=("werkzeug",)),
        mock.patch("odoo.http._serve.get_ir_http", return_value=ir_http),
    ):
        served._update_served_exception(_BUG)
    assert handled == [_BUG]


def test_both_json_dispatchers_serialise_errors_under_the_debugger():
    from odoo.http.dispatcher import HttpDispatcher, Json2Dispatcher, JsonRPCDispatcher

    assert JsonRPCDispatcher.serializes_errors_in_dev_mode is True
    assert Json2Dispatcher.serializes_errors_in_dev_mode is True, (
        "a JSON client cannot use an HTML debugger page"
    )
    assert HttpDispatcher.serializes_errors_in_dev_mode is False
