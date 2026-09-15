import logging

_logger = logging.getLogger(__name__)

CREDIT_TYPE_XMLIDS = [
    "doc_type_id_document",
    "doc_type_contract",
    "doc_type_promissory_note",
    "doc_type_warranty",
    "doc_type_credit_application",
    "doc_type_proof_of_address",
    "doc_type_authorized_signatures",
]


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE ir_model_data
        SET module = 'credit_management'
        WHERE module = 'document_compliance' AND name = ANY(%s)
        """,
        [CREDIT_TYPE_XMLIDS],
    )
    _logger.info("Handed %d credit document types to credit_management", cr.rowcount)

    cr.execute(
        "ALTER TABLE document_document "
        "DROP CONSTRAINT IF EXISTS document_document_legal_number_uniq"
    )

    cr.execute(
        """
        UPDATE document_document d
        SET renewal_document_id = NULL
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY renewal_document_id ORDER BY id)
                       AS position
            FROM document_document
            WHERE renewal_document_id IS NOT NULL
        ) ranked
        WHERE d.id = ranked.id AND ranked.position > 1
        RETURNING d.id, d.name
        """
    )
    for document_id, name in cr.fetchall():
        _logger.warning(
            "Document %s (%r) claimed to renew a document another renewal already "
            "renews; its renewal link was cleared so the chain stays a single line.",
            document_id,
            name,
        )

    cr.execute(
        """
        UPDATE document_document d
        SET renewal_document_id = NULL
        WHERE renewal_document_id IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM document_document p
              WHERE p.id = d.renewal_document_id
                AND p.renewed_by_document_id IS NOT NULL
                AND p.renewed_by_document_id != d.id
          )
        """
    )
    if cr.rowcount:
        _logger.warning(
            "%d documents pointed at a parent whose recorded renewal was a different "
            "document; those links were cleared in favour of the recorded one.",
            cr.rowcount,
        )
