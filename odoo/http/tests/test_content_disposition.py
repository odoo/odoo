import pytest
from werkzeug.test import EnvironBuilder
from werkzeug.utils import send_file

from odoo.http.wrappers import prepare_content_disposition_header


@pytest.mark.parametrize(
    "name", ["a.pdf", 'résumé "x".pdf', "日本語.txt", "semi;colon, comma.csv"]
)
def test_the_header_is_the_one_send_file_writes(name):
    from io import BytesIO

    sent = send_file(
        BytesIO(b""),
        EnvironBuilder().get_environ(),
        download_name=name,
        as_attachment=True,
        mimetype="application/octet-stream",
    )
    assert (
        prepare_content_disposition_header(name) == sent.headers["Content-Disposition"]
    )


def test_an_ascii_name_needs_no_extended_form():
    assert prepare_content_disposition_header("a.pdf") == "attachment; filename=a.pdf"


def test_a_non_ascii_name_carries_an_ascii_fallback():
    header = prepare_content_disposition_header('résumé "x".pdf')
    assert 'filename="resume \\"x\\".pdf"' in header
    assert "filename*=UTF-8''r%C3%A9sum%C3%A9%20%22x%22.pdf" in header


def test_line_breaks_cannot_split_the_header():
    header = prepare_content_disposition_header("a\r\nSet-Cookie: x=1.pdf")
    assert "\r" not in header and "\n" not in header


def test_content_disposition_inline():
    assert prepare_content_disposition_header("a.pdf", "inline").startswith("inline; ")


def test_content_disposition_rejects_bad_type():
    with pytest.raises(ValueError, match="Invalid disposition_type"):
        prepare_content_disposition_header("a.pdf", "bogus")
