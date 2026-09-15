import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE document_type dt
        SET applies_to = scoped.res_model
        FROM (
            SELECT document_type_id, MIN(res_model) AS res_model
            FROM document_document
            WHERE document_type_id IS NOT NULL
              AND res_model IS NOT NULL
              AND res_id IS NOT NULL
            GROUP BY document_type_id
            HAVING COUNT(DISTINCT res_model) = 1
        ) AS scoped
        WHERE dt.id = scoped.document_type_id
          AND dt.applies_to = 'all'
          AND scoped.res_model IN (
              SELECT model FROM ir_model WHERE model = scoped.res_model
          )
        """
    )
    _logger.info("Inferred applies_to for %d document types", cr.rowcount)

    cr.execute(
        """
        SELECT COUNT(*) FROM document_type
        WHERE applies_to = 'all' AND is_mandatory = true
        """
    )
    ambiguous = cr.fetchone()[0]
    if ambiguous:
        _logger.warning(
            "%d mandatory document types still apply to All Entities. Review "
            "their scope: each is required of every entity in the compliance "
            "report.",
            ambiguous,
        )
