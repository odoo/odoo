from odoo.http.wrappers import prepare_content_disposition_header


def test_content_disposition_encodes_unicode_and_quotes():
    header = prepare_content_disposition_header('résumé "x".pdf')
    assert header.startswith("attachment; filename*=UTF-8''")
    assert "r%C3%A9sum%C3%A9" in header
    assert '"' not in header


def test_content_disposition_inline():
    assert prepare_content_disposition_header("a.pdf", "inline").startswith("inline; ")


def test_content_disposition_rejects_bad_type():
    import pytest

    with pytest.raises(ValueError, match="Invalid disposition_type"):
        prepare_content_disposition_header("a.pdf", "bogus")
