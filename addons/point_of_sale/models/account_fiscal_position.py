from odoo import models, api, _
from odoo.exceptions import UserError


class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _inherit = ['account.fiscal.position', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        fp_ids = [preset['fiscal_position_id'] for preset in data['pos.preset']]
        partner_fp_ids = list({partner['fiscal_position_id'] for partner in data['res.partner'] if partner['fiscal_position_id']}) if 'res.partner' in data.keys() else []
        return [('id', 'in', config.fiscal_position_ids.ids + fp_ids + partner_fp_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'display_name', 'tax_map', 'tax_ids']

    def action_archive(self):
        configs = self.env['pos.config'].search([('default_fiscal_position_id', 'in', self.ids)])
        configs.default_fiscal_position_id = False
        return super().action_archive()

    def _check_pos_order_usage(self):
        fpos_ids = self.ids
        if fpos_ids and self.env['pos.order'].sudo().search_count([
            ('fiscal_position_id', 'in', fpos_ids),
            ('state', 'in', ['paid', 'done', 'invoiced']),
        ], limit=1):
            raise UserError(_(
                "You cannot modify the taxes of a fiscal position used in a POS order. "
                "You should archive it and create a new one."
            ))

    def write(self, vals):
        if 'tax_ids' in vals:
            self._check_pos_order_usage()
        return super().write(vals)
