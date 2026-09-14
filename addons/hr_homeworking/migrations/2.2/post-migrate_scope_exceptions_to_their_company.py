import logging

_logger = logging.getLogger(__name__)

_COMPANY_SCOPED = "[('company_id', 'in', company_ids)]"


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_rule r
           SET domain_force = %s
          FROM ir_model_data d
         WHERE d.model = 'ir.rule'
           AND d.module = 'hr_homeworking'
           AND d.name = 'homeworking_admin_rule'
           AND r.id = d.res_id
           AND r.domain_force = %s
        """,
        (_COMPANY_SCOPED, "[(1, '=', 1)]"),
    )
    if cr.rowcount:
        _logger.info(
            "hr_homeworking: the exceptional-location rule for HR users was "
            "[(1, '=', 1)], which let an HR user of one company read, write and "
            "resolve the employee name of an exception belonging to another; it "
            "is scoped to the user's allowed companies now"
        )
