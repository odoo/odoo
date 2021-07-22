# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    check_id = fields.Many2one('account.payment', string='Check')
    amount = fields.Monetary(compute='_compute_amount', readonly=False, store=True)
    third_check_issue_date = fields.Date()
    third_check_from_state = fields.Char(compute='_compute_third_check_from_state')
    third_check_bank_id = fields.Many2one('res.bank', compute='_compute_third_check_data', store=True, readonly=False)
    third_check_issuer_vat = fields.Char(store=True, compute='_compute_third_check_data', readonly=False)
    third_check_issuer_name = fields.Char(compute='_compute_third_check_issuer_name', store=True, readonly=False)

    @api.depends('payment_method_id.code', 'partner_id')
    def _compute_third_check_data(self):
        new_third_checks = self.filtered(lambda x: x.payment_method_id.code == 'new_third_checks')
        (self - new_third_checks).update({'third_check_bank_id': False, 'third_check_issuer_vat': False, 'third_check_issue_date': False})
        for rec in new_third_checks:
            rec.update({
                'third_check_bank_id': rec.partner_id.bank_ids and rec.partner_id.bank_ids[0].bank_id or False,
                'third_check_issuer_vat': rec.partner_id.vat,
                'third_check_issue_date': fields.Date.context_today(rec),
            })

    @api.depends('third_check_issuer_vat')
    def _compute_third_check_issuer_name(self):
        """ We suggest owner name from owner vat """
        with_vat = self.filtered(lambda x: x.third_check_issuer_vat)
        (self - with_vat).third_check_issuer_name = False
        for rec in with_vat:
            rec.third_check_issuer_name = self.search(
                [('third_check_issuer_vat', '=', self.third_check_issuer_vat)], limit=1).third_check_issuer_name or self.partner_id.name


    @api.depends('payment_method_code', 'payment_type')
    def _compute_third_check_from_state(self):
        moved_third_checks = self.filtered(lambda x: x.payment_method_id.code in ['in_third_checks', 'out_third_checks'])
        (self - moved_third_checks).third_check_from_state = False
        for rec in moved_third_checks:
            from_state, to_state  = self.env['account.payment']._get_checks_states_model(
                self.payment_method_code, self.payment_type, False)
            rec.third_check_from_state = from_state

    @api.depends('check_id.amount')
    def _compute_amount(self):
        for rec in self.filtered('check_id'):
            rec.amount = rec.check_id.amount

    def _create_payment_vals_from_wizard(self):
        vals = super()._create_payment_vals_from_wizard()
        vals.update({
            'check_id': self.check_id.id,
            'third_check_issue_date': self.third_check_issue_date,
            'third_check_bank_id': self.third_check_bank_id,
            'third_check_issuer_vat': self.third_check_issuer_vat,
            'third_check_issuer_name': self.third_check_issuer_name,
        })
        return vals

    @api.onchange('third_check_issue_date', 'check_payment_date')
    def onchange_date(self):
        for rec in self:
            if rec.third_check_issue_date and rec.check_payment_date and rec.third_check_issue_date > rec.check_payment_date:
                raise UserError(_('Check Payment Date must be greater than Issue Date'))
