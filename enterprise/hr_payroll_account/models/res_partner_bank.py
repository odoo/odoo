# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    has_alt_bank_account = fields.Boolean(compute="_compute_has_alt_bank_account")

    @api.depends('partner_id')
    def _compute_has_alt_bank_account(self):
        for bank_partner in self:
            if partner := bank_partner.partner_id:
                bank_partner.has_alt_bank_account = any(bank != bank_partner for bank in partner.bank_ids)
            else:
                bank_partner.has_alt_bank_account = False

    def create(self, vals_list):
        res = super().create(vals_list)
        if self.env.context.get('from_employee_bank_account'):
            res._set_bank_account()
        return res

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('from_employee_bank_account') and 'partner_id' in vals:
            self._set_bank_account()
        return res

    def _set_bank_account(self):
        for partner_bank in self:
            partner_bank.partner_id.employee_ids.write({'bank_account_id': partner_bank.id})
