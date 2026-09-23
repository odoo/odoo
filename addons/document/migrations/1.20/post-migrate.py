import logging

from odoo import SUPERUSER_ID, api
from odoo.libs.filesystem import get_extension
from odoo.libs.sql import SQL

_logger = logging.getLogger(__name__)

# get_extension used to answer mimetypes.guess_extension for an extension
# longer than four characters; it keeps the file's own now, and a row still
# holding the old answer is the derived value, not an operator's choice
FORMER_EXTENSIONS = {
    "markdown": "md",
    "mhtml": "eml",
    "texinfo": "texi",
    "3gpp2": "3g2",
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    documents = (
        env["document.document"]
        .with_context(active_test=False)
        .search(
            [
                ("type", "=", "binary"),
                ("file_extension", "in", list(FORMER_EXTENSIONS.values())),
            ]
        )
    )
    corrected: dict[str, list[int]] = {}
    for document in documents:
        source = document.shortcut_document_id.name or document.name or ""
        extension = get_extension(source.strip()).lstrip(".")
        if FORMER_EXTENSIONS.get(extension) == document.file_extension:
            corrected.setdefault(extension, []).append(document.id)
    for extension, ids in corrected.items():
        cr.execute(
            SQL(
                "UPDATE document_document SET file_extension = %s WHERE id = ANY(%s)",
                extension,
                ids,
            )
        )
    if corrected:
        env["document.document"].invalidate_model(["file_extension"])
        _logger.info(
            "document: file_extension corrected on %s document(s): %s",
            sum(map(len, corrected.values())),
            {extension: len(ids) for extension, ids in corrected.items()},
        )
