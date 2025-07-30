from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_latam_manual_checks = fields.Boolean(
        string='Use electronic and deferred checks',
        help="* Allows putting numbers manually\n"
             "* Enables Check Cash-In Date feature\n"
             "* Disables printing"
    )

    @api.constrains('l10n_latam_manual_checks', 'check_manual_sequencing')
    def _check_l10n_latam_manual_checks(self):
        """ Protect from setting check_manual_sequencing (Manual Numbering) + Use electronic/deferred checks for these reasons
        * Printing checks for manual checks (electronic/deferred) is not implemented and using a "check printing" option together with the manual
          checks is confusing
        * The next check number field shown when choosing "Manual Numbering" don't have any meaning when using manual checks (electronic/deferred)
        * Some methods of account_check_printing module behave differently if "Manual Numbering" is configured
        """
        recs = self.filtered(
            lambda x: x.check_manual_sequencing and x.l10n_latam_manual_checks)
        if recs:
            raise UserError(_(
                "Manual checks (electronic/deferred) can't be used together with check manual sequencing (check printing functionality), "
                "please choose one or the other. Journals: %s", ",".join(recs.mapped("name"))))

    @api.constrains("inbound_payment_method_line_ids", "outbound_payment_method_line_ids")
    def _check_payment_method_line_ids_multiplicity(self):
        super()._check_payment_method_line_ids_multiplicity()
        # Ensure that only one instance of specific third-party check payment methods
        # exists in a journal.
        restricted_methods = {"in_third_party_checks", "out_third_party_checks", "return_third_party_checks"}
        for journal in self:
            journal_payment_method_lines = (
                journal.inbound_payment_method_line_ids + journal.outbound_payment_method_line_ids
            )

            for method_code in restricted_methods:
                if len(journal_payment_method_lines.filtered(lambda x: x.payment_method_id.code == method_code)) > 1:
                    raise ValidationError(
                        _("The payment method '%(method)s' cannot be added more than once in the journal '%(journal)s'.",
                        method=method_code, journal=journal.name)
                    )
