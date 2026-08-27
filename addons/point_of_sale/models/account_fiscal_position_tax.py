from odoo import models, api, _
from odoo.exceptions import UserError


class AccountFiscalPositionTax(models.Model):
    _name = 'account.fiscal.position.tax'
    _inherit = ['account.fiscal.position.tax', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('position_id', 'in', [fpos['id'] for fpos in data['account.fiscal.position']['data']])]

    def _check_pos_order_usage(self):
        fpos_ids = self.position_id.ids
        if fpos_ids and self.env["pos.order"].sudo().search_count([
            ("fiscal_position_id", "in", fpos_ids),
            ("state", "in", ['paid', 'done', 'invoiced'])
        ]):
            raise UserError(_(
                    "You cannot modify a fiscal position used in a POS order. "
                    "You should archive it and create a new one."
                ))

    def write(self, vals):
        self._check_pos_order_usage()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_in_pos_order(self):
        self._check_pos_order_usage()
