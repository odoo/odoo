# -*- coding: utf-8 -*-

from openerp import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    contracts_count = fields.Integer(compute='_compute_contracts_count', string="Contracts")

    @api.multi
    def _compute_contracts_count(self):
        analytic_account_data = self.env['account.analytic.account'].read_group([('partner_id', 'in', self.ids), ('type', '=', 'contract'), ('state', 'in', ('open', 'pending'))], ['partner_id'], ['partner_id'])
        result = dict((data['partner_id'][0], data['partner_id_count']) for data in analytic_account_data)
        for partner in self:
            partner.contracts_count = result.get(partner.id, 0)
