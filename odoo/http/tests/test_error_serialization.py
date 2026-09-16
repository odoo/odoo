import types


def test_serialize_exception_masks_infra_errors_for_clients_only():
    import psycopg

    from odoo.http import _request_stack
    from odoo.http._error_serialization import serialize_exception

    secret_os = OSError("/srv/filestore/prod/.session/secret-layout")
    secret_pg = psycopg.OperationalError("UPDATE res_users SET password=...")

    assert "filestore" in serialize_exception(secret_os)["message"]
    assert "res_users" in serialize_exception(secret_pg)["message"]

    _request_stack.push(types.SimpleNamespace())
    try:
        for exc in (secret_os, secret_pg):
            data = serialize_exception(exc)
            assert data["message"] == "Internal Server Error"
            assert data["arguments"] == ()
            assert data["name"].endswith(type(exc).__name__)
        assert serialize_exception(ValueError("bad domain"))["message"] == "bad domain"
    finally:
        _request_stack.pop()
