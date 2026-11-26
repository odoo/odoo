from odoo import api, models
from odoo.fields import Domain


class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _inherit = ['account.fiscal.position', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        domain = Domain('id', 'in', data['pos.config'].fiscal_position_ids.ids + data['pos.preset'].fiscal_position_id.ids)
        if data['res.partner']:
            domain |= Domain(self._check_company_domain(data['pos.config'].company_id))
        return list(domain)

    @api.model
    def _load_pos_data_dependencies(self):
        return ['res.partner', 'pos.preset']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'display_name', 'tax_map', 'tax_ids']

    def action_archive(self):
        configs = self.env['pos.config'].search([('default_fiscal_position_id', 'in', self.ids)])
        configs.default_fiscal_position_id = False
        return super().action_archive()
