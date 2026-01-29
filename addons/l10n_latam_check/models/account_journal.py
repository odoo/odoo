from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
