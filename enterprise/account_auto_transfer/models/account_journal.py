from odoo import models, api
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.ondelete(at_uninstall=True)
    def _unlink_cascade_transfer_model(self):
        if self.env.context.get(MODULE_UNINSTALL_FLAG):  # only cascade when switching CoA
            self.env['account.transfer.model'].search([('journal_id', 'in', self.ids)]).unlink()
