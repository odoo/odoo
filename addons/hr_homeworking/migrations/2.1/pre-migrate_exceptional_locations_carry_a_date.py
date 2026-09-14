import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("DELETE FROM hr_employee_location WHERE date IS NULL")
    if cr.rowcount:
        _logger.info(
            "hr.employee.location: deleted %s date-less rows; the model now only "
            "holds exceptions, and an exception without a date is unreachable "
            "by every reader of it",
            cr.rowcount,
        )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = 'res_users_view_form_profile'
         WHERE module = 'hr_homeworking'
           AND name = 'res_useurs_view_form_profile'
        """
    )
    if cr.rowcount:
        _logger.info("hr_homeworking: res_useurs_view_form_profile xmlid typo fixed")
