from __future__ import annotations

from odoo.libs.documents import Document

from . import readers  # noqa: F401  registers the readers, not imported for a name


def document_of(attachment, data: bytes | None = None, **options) -> Document:
    """Wrap an attachment as a document, fetching a remote blob if there is one.

    `raw` holds only what this database stores, so reading it made every
    cloud-stored attachment look like an empty file to every strategy -- no
    text, no fields, no error. `_fetch_content` answers the same bytes for a
    local blob and goes and gets a remote one.

    `data` is for a caller that already holds the bytes -- it had to look at
    them to decide whether there was a document at all -- and spares a second
    trip to the provider for the same blob.
    """
    attachment.check_singleton()
    if data is None:
        data = attachment._fetch_content()
    return Document(
        data, attachment.mimetype or "", attachment.name or "", **options
    )
