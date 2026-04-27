# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    it_fiscal_printer_https = fields.Boolean(string='Use HTTPS')
    it_fiscal_printer_ip = fields.Char(string='Fiscal Printer IP')
    it_fiscal_cash_drawer = fields.Boolean(string='Fiscal Printer Cash Drawer')

    def _create_journal_and_payment_methods(self, cash_ref=None, cash_journal_vals=None):
        journal, pm_ids = super()._create_journal_and_payment_methods(cash_ref, cash_journal_vals)
        if self.env.company.country_id.code == 'IT':
            for pm in self.env['pos.payment.method'].browse(pm_ids):
                if pm.type == 'cash':
                    pm.it_payment_code = '0'
                elif pm.type == 'bank':
                    pm.it_payment_code = '2'
                    pm.it_payment_index = 1
                elif pm.type == 'pay_later':
                    pm.it_payment_code = '5'
        return journal, pm_ids

    def get_limited_partners_loading(self):
        partner_ids = super().get_limited_partners_loading()
        if (self.env.company.partner_id.id,) not in partner_ids:
            partner_ids.append((self.env.company.partner_id.id,))
        return partner_ids
