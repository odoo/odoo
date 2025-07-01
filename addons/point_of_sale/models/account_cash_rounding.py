from odoo import api, models, _
from odoo.exceptions import UserError


class AccountCashRounding(models.Model):
    _inherit = 'account.cash.rounding'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_pos_config(self):
        if self.env['pos.config'].search_count([('rounding_method', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot delete a rounding method that is used in a Point of Sale configuration.'))
