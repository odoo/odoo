from odoo import models


class L10nAePintCheckMixin(models.AbstractModel):
    """ Build the account.move.send alerts for the PINT AE rules a record breaks.

    Models carrying PINT AE data implement `_l10n_ae_pint_group_by_error_code` with their own
    rules; the grouping and the alert values are the same for all of them.
    """
    _name = 'l10n.ae.pint.check.mixin'
    _description = "PINT AE Compliance Checks"

    def _l10n_ae_pint_group_by_error_code(self):
        """Return the error tuple for this record, or False when it is compliant."""
        self.ensure_one()
        return False

    def _l10n_ae_pint_action_text(self):
        """Label of the button the alert offers to review the offending records."""
        return self.env._("View Record(s)")

    def _l10n_ae_pint_export_check(self):
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda r: r._l10n_ae_pint_group_by_error_code()).items():
            if not error_tuple:
                continue
            error_vals = dict(error_tuple)
            alert_vals[error_vals['error_code']] = {
                'message': error_vals['message'],
                'level': error_vals['level'],
                'action': invalid_records._get_records_action(),
                'action_text': invalid_records._l10n_ae_pint_action_text(),
            }
        return alert_vals
