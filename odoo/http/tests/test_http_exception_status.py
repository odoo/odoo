import werkzeug.exceptions
from werkzeug.exceptions import HTTPException

from odoo.http import Response, prepare_exception_response


class _CodelessSubclass(HTTPException):
    pass


def test_a_bare_http_exception_becomes_a_500():
    response = prepare_exception_response(HTTPException("no status here"))
    assert response.status_code == 500
    assert b"no status here" in response.get_data()


def test_a_subclass_that_forgot_its_code_becomes_a_500():
    assert prepare_exception_response(_CodelessSubclass()).status_code == 500


def test_a_real_status_is_left_alone():
    response = prepare_exception_response(werkzeug.exceptions.NotFound("nope"))
    assert response.status_code == 404
    assert b"nope" in response.get_data()


def test_abort_with_a_response_is_delivered_verbatim():
    attached = Response(b"body", status=204)
    exc = werkzeug.exceptions.HTTPException(response=attached._wrapped__)
    assert exc.code is None

    response = prepare_exception_response(exc)
    assert response.status_code == 204


def test_the_result_is_always_the_package_facade():
    assert isinstance(prepare_exception_response(HTTPException()), Response)
    assert isinstance(prepare_exception_response(werkzeug.exceptions.Gone()), Response)


def test_werkzeug_is_left_unpatched():
    assert "_odoo_original_get_response" not in vars(werkzeug.exceptions)
    assert "_odoo_original_abort" not in vars(werkzeug.exceptions)
    assert HTTPException.get_response.__module__ == "werkzeug.exceptions"
