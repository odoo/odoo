"""Database-free tests for ``ir.attachment`` pure methods.

Covers ``_compute_checksum()`` (SHA-1 hex digest) and
``_compute_mimetype()`` (multi-fallback MIME detection).

Run with::

    python -m pytest core/tests/models/test_ir_attachment.py -v
"""

import base64
import hashlib

# ── _compute_checksum ─────────────────────────────────────────


class TestComputeChecksum:
    """``_compute_checksum``: SHA-1 hex digest of binary data."""

    def test_standard_data(self, env):
        """Known content produces expected SHA-1."""
        data = b"hello world"
        att = env["ir.attachment"].browse()
        result = att._compute_checksum(data)
        assert result == hashlib.sha1(b"hello world").hexdigest()

    def test_empty_bytes(self, env):
        """Empty bytes → SHA-1 of empty string (not None)."""
        att = env["ir.attachment"].browse()
        result = att._compute_checksum(b"")
        assert result == hashlib.sha1(b"").hexdigest()
        assert len(result) == 40  # SHA-1 hex digest length

    def test_none_input(self, env):
        """None → treated as empty bytes."""
        att = env["ir.attachment"].browse()
        result = att._compute_checksum(None)
        assert result == hashlib.sha1(b"").hexdigest()

    def test_binary_content(self, env):
        """Non-UTF8 binary data is hashed correctly."""
        data = bytes(range(256))
        att = env["ir.attachment"].browse()
        result = att._compute_checksum(data)
        assert result == hashlib.sha1(data).hexdigest()


# ── _compute_mimetype ─────────────────────────────────────────


class TestComputeMimetype:
    """``_compute_mimetype``: multi-fallback MIME type detection.

    Priority: explicit mimetype → name extension → URL extension → raw content.
    """

    def test_explicit_mimetype(self, env):
        """Explicit mimetype in values takes precedence."""
        att = env["ir.attachment"].browse()
        result = att._compute_mimetype({"mimetype": "text/html"})
        assert result == "text/html"

    def test_from_filename(self, env):
        """MIME guessed from file extension."""
        att = env["ir.attachment"].browse()
        result = att._compute_mimetype({"name": "report.pdf"})
        assert result == "application/pdf"

    def test_from_url(self, env):
        """MIME guessed from URL path extension."""
        att = env["ir.attachment"].browse()
        result = att._compute_mimetype({"url": "/web/content/logo.png?download=true"})
        assert result == "image/png"

    def test_url_query_stripped(self, env):
        """Query string stripped before guessing MIME from URL."""
        att = env["ir.attachment"].browse()
        result = att._compute_mimetype({"url": "/files/data.csv?v=2"})
        assert result == "text/csv"

    def test_from_raw_content(self, env):
        """MIME detected from raw binary content (magic bytes)."""
        att = env["ir.attachment"].browse()
        # PDF magic bytes — libmagic recognizes these reliably
        pdf_bytes = b"%PDF-1.4 fake content"
        result = att._compute_mimetype({"raw": pdf_bytes})
        assert result == "application/pdf"

    def test_from_datas_base64(self, env):
        """MIME detected from base64-encoded datas field."""
        att = env["ir.attachment"].browse()
        # PDF magic bytes
        pdf_bytes = b"%PDF-1.4 fake content"
        datas = base64.b64encode(pdf_bytes).decode()
        result = att._compute_mimetype({"datas": datas})
        assert result == "application/pdf"

    def test_empty_values(self, env):
        """No clues → default 'application/octet-stream'."""
        att = env["ir.attachment"].browse()
        result = att._compute_mimetype({})
        assert result == "application/octet-stream"

    def test_uppercase_lowered(self, env):
        """Explicit MIME type is lowercased."""
        att = env["ir.attachment"].browse()
        result = att._compute_mimetype({"mimetype": "TEXT/HTML"})
        assert result == "text/html"

    def test_name_takes_precedence_over_url(self, env):
        """Name extension checked before URL when no explicit mimetype."""
        att = env["ir.attachment"].browse()
        result = att._compute_mimetype({
            "name": "document.pdf",
            "url": "/files/image.png",
        })
        assert result == "application/pdf"
