from unittest import mock

import werkzeug.exceptions

from odoo.http import application

_BUG = RuntimeError("boom")


def test_no_handover_without_an_attached_debugger():
    assert application.debugger_attached is False, (
        "importing odoo.http must not attach a debugger"
    )
    assert application._is_debugger_handover_required(None, _BUG) is False


def test_handover_once_a_debugger_is_attached():
    with mock.patch.object(application, "debugger_attached", True):
        assert application._is_debugger_handover_required(None, _BUG) is True


def test_a_serialising_dispatcher_is_exempt():
    req = mock.Mock()
    req.dispatcher.serializes_errors_in_dev_mode = True
    with mock.patch.object(application, "debugger_attached", True):
        assert application._is_debugger_handover_required(req, _BUG) is False
    req.dispatcher.serializes_errors_in_dev_mode = False
    with mock.patch.object(application, "debugger_attached", True):
        assert application._is_debugger_handover_required(req, _BUG) is True


def test_an_http_answer_is_never_a_debugger_case():
    req = mock.Mock()
    req.dispatcher.serializes_errors_in_dev_mode = False
    with mock.patch.object(application, "debugger_attached", True):
        for answer in (
            werkzeug.exceptions.NotFound(),
            werkzeug.exceptions.Forbidden(),
            werkzeug.exceptions.BadRequest(),
        ):
            assert application._is_debugger_handover_required(req, answer) is False
        assert application._is_debugger_handover_required(
            req, werkzeug.exceptions.InternalServerError()
        )
        assert application._is_debugger_handover_required(
            req, werkzeug.exceptions.HTTPException()
        ), "a status-less exception is a defect, not an answer"


def test_both_json_dispatchers_serialise_errors_under_the_debugger():
    from odoo.http.dispatcher import HttpDispatcher, Json2Dispatcher, JsonRPCDispatcher

    assert JsonRPCDispatcher.serializes_errors_in_dev_mode is True
    assert Json2Dispatcher.serializes_errors_in_dev_mode is True, (
        "a JSON client cannot use an HTML debugger page"
    )
    assert HttpDispatcher.serializes_errors_in_dev_mode is False
