from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_latam_use_checkbooks = fields.Boolean(
        string='Use checkbooks?',
        copy=False,
        help="Check this option if you want to have a checkbook control and/or need to use deferred checks.\n"
        "This option disables the printing functionality."
    )

    @api.constrains('l10n_latam_use_checkbooks', 'check_manual_sequencing')
    def _check_l10n_latam_use_checkbooks(self):
        """ Protect from setting check_manual_sequencing (Manual Numbering) + checkbooks for these reasons
        * Printing checks on checkbooks is not implemented and using a "check printing" option together with checkbooks is confusing
        * The next check number field shown when choosing "Manual Numbering" don't have any meaning when using checkbooks
        * Some methods of account_check_printing module behavis differently if "Manual Numbering" is configured
        """
        recs = self.filtered(
            lambda x: x.check_manual_sequencing and x.l10n_latam_use_checkbooks)
        if recs:
            raise UserError(_(
                "Checkbooks can't be used together with check manual sequencing (check printing functionality), "
                "please choose one or the other. Journal ids: %s", recs.ids))
