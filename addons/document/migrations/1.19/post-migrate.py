import logging

from odoo.addons.document.models.document_document import new_document_token

_logger = logging.getLogger(__name__)

# A uuid4 token draws its 22 characters from 64 and shows about 18 distinct
# ones; fewer than 10 is a token somebody typed while it was still writable.
MIN_DISTINCT_CHARACTERS = 10


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT id
          FROM document_document
         WHERE (SELECT count(DISTINCT c)
                  FROM regexp_split_to_table(document_token, '') AS c) < %s
        """,
        [MIN_DISTINCT_CHARACTERS],
    )
    document_ids = [row[0] for row in cr.fetchall()]
    for document_id in document_ids:
        cr.execute(
            "UPDATE document_document SET document_token = %s WHERE id = %s",
            [new_document_token(), document_id],
        )
    if document_ids:
        _logger.info(
            "document: rotated %s share token(s) that were not server-generated: %s",
            len(document_ids),
            document_ids,
        )
