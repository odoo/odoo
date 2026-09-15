import logging

_logger = logging.getLogger(__name__)

OLD_CONSTRAINTS = (
    "documents_type_code_company_uniq",
    "document_type_code_company_uniq",
)
REDUNDANT_INDEX = "document_document__legal_number_index"


def migrate(cr, version):
    if not version:
        return

    for constraint in OLD_CONSTRAINTS:
        cr.execute(f"ALTER TABLE document_type DROP CONSTRAINT IF EXISTS {constraint}")

    cr.execute(f"DROP INDEX IF EXISTS {REDUNDANT_INDEX}")
    _logger.info("Dropped redundant index %s if it existed", REDUNDANT_INDEX)

    cr.execute(
        """
        SELECT id, code
        FROM (
            SELECT id, code,
                   ROW_NUMBER() OVER (
                       PARTITION BY code, COALESCE(company_id, -1) ORDER BY id
                   ) AS position
            FROM document_type
        ) ranked
        WHERE position > 1
        ORDER BY id
        """
    )
    duplicates = cr.fetchall()
    if not duplicates:
        _logger.info("No duplicate document type codes; index can be built as is.")
        return

    for type_id, code in duplicates:
        new_code = f"{code}-{type_id}"
        cr.execute(
            "UPDATE document_type SET code = %s WHERE id = %s", [new_code, type_id]
        )
        _logger.warning(
            "Document type %s had duplicate code %r; renamed to %r. Review "
            "whether these were meant to be a single type.",
            type_id,
            code,
            new_code,
        )
