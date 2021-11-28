# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    check_id = fields.Many2one('account.payment', string='Check')
    third_check_bank_id = fields.Many2one('res.bank', compute='_compute_third_check_data', store=True, readonly=False)
    third_check_issuer_vat = fields.Char(store=True, compute='_compute_third_check_data', readonly=False)

    @api.depends('payment_method_line_id.code', 'partner_id')
    def _compute_third_check_data(self):
        new_third_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        (self - new_third_checks).update({'third_check_bank_id': False, 'third_check_issuer_vat': False})
        for rec in new_third_checks:
            rec.update({
                'third_check_bank_id': rec.partner_id.bank_ids and rec.partner_id.bank_ids[0].bank_id or False,
                'third_check_issuer_vat': rec.partner_id.vat,
            })

    @api.onchange('check_id')
    def _onchange_amount(self):
        for rec in self.filtered('check_id'):
            rec.amount = rec.check_id.amount

    def _create_payment_vals_from_wizard(self):
        vals = super()._create_payment_vals_from_wizard()
        vals.update({
            'check_id': self.check_id.id,
            'third_check_bank_id': self.third_check_bank_id,
            'third_check_issuer_vat': self.third_check_issuer_vat,
        })
        return vals

    @api.onchange('check_number')
    def _onchange_check_number(self):
        for rec in self.filtered(lambda x: x.journal_id.company_id.country_id.code == "AR"):
            try:
                if rec.check_number:
                    rec.check_number = '%08d' % int(rec.check_number)
            except Exception:
                pass
