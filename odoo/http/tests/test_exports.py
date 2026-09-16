import types

import pytest

import odoo.http


def test_all_names_resolve():
    missing = [n for n in odoo.http.__all__ if not hasattr(odoo.http, n)]
    assert not missing, f"odoo.http.__all__ names missing from the module: {missing}"


def test_all_has_no_duplicates():
    dupes = {n for n in odoo.http.__all__ if odoo.http.__all__.count(n) > 1}
    assert not dupes, f"duplicate names in odoo.http.__all__: {dupes}"


def test_every_public_name_is_declared_in_all():
    declared = set(odoo.http.__all__)
    published = {
        name
        for name, value in vars(odoo.http).items()
        if not name.startswith("__") and not isinstance(value, types.ModuleType)
    }
    undeclared = sorted(published - declared)
    assert not undeclared, (
        f"reachable as odoo.http.<name> but absent from __all__: {undeclared}. "
        f"Declare them, or stop re-exporting them from __init__."
    )


def test_abort_hands_werkzeug_the_wrapped_response():
    import werkzeug.exceptions

    import odoo.http

    assert werkzeug.exceptions.abort.__module__ == "werkzeug.exceptions"
    with pytest.raises(werkzeug.exceptions.HTTPException) as caught:
        odoo.http.abort(odoo.http.Response("x", status=204))
    assert caught.value.response is not None
    assert not isinstance(caught.value.response, odoo.http.Response), (
        "abort unwraps the proxy before handing werkzeug the response"
    )
