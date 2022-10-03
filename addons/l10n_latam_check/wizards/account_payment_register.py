# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_latam_check_id = fields.Many2one('account.payment', string='Check')
    l10n_latam_check_bank_id = fields.Many2one(
        'res.bank', compute='_compute_l10n_latam_check_data', store=True, readonly=False, string='Check Bank')
    l10n_latam_check_issuer_vat = fields.Char(
        store=True, compute='_compute_l10n_latam_check_data', readonly=False, string='Check Issuer VAT')
    l10n_latam_check_number = fields.Char(
        string="Check Number", store=True, readonly=False, copy=False,
        compute='_compute_l10n_latam_check_number', inverse='_inverse_l10n_latam_check_number',
    )
    l10n_latam_use_checkbooks = fields.Boolean(related='journal_id.l10n_latam_use_checkbooks')
    l10n_latam_checkbook_type = fields.Selection(related='l10n_latam_checkbook_id.type')
    l10n_latam_checkbook_id = fields.Many2one(
        'l10n_latam.checkbook', 'Checkbook', store=True, compute='_compute_l10n_latam_checkbook', readonly=False)
    l10n_latam_check_payment_date = fields.Date(string='Check Payment Date')

    @api.depends('payment_method_line_id.code', 'journal_id.l10n_latam_use_checkbooks')
    def _compute_l10n_latam_checkbook(self):
        with_checkbooks = self.filtered(
            lambda x: x.payment_method_line_id.code == 'check_printing' and x.journal_id.l10n_latam_use_checkbooks)
        (self - with_checkbooks).l10n_latam_checkbook_id = False
        for rec in with_checkbooks:
            checkbook = rec.journal_id.with_context(active_test=True).l10n_latam_checkbook_ids
            rec.l10n_latam_checkbook_id = checkbook and checkbook[0] or False

    @api.depends('journal_id', 'payment_method_code', 'l10n_latam_checkbook_id')
    def _compute_l10n_latam_check_number(self):
        for rec in self.filtered('l10n_latam_checkbook_id'):
            rec.l10n_latam_check_number = rec.l10n_latam_checkbook_id.sequence_id.get_next_char(
                rec.l10n_latam_checkbook_id.next_number)

    def _inverse_l10n_latam_check_number(self):
        for rec in self:
            if rec.l10n_latam_check_number:
                sequence = rec.journal_id.check_sequence_id.sudo()
                sequence.padding = len(rec.l10n_latam_check_number)

    @api.depends('payment_method_line_id.code', 'partner_id')
    def _compute_l10n_latam_check_data(self):
        new_third_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        (self - new_third_checks).update({'l10n_latam_check_bank_id': False, 'l10n_latam_check_issuer_vat': False})
        for rec in new_third_checks:
            rec.update({
                'l10n_latam_check_bank_id': rec.partner_id.bank_ids and rec.partner_id.bank_ids[0].bank_id or False,
                'l10n_latam_check_issuer_vat': rec.partner_id.vat,
            })

    @api.onchange('l10n_latam_check_id')
    def _onchange_amount(self):
        for rec in self.filtered('l10n_latam_check_id'):
            rec.amount = rec.l10n_latam_check_id.amount

    def _create_payment_vals_from_wizard(self):
        vals = super()._create_payment_vals_from_wizard()
        vals.update({
            'l10n_latam_check_id': self.l10n_latam_check_id.id,
            'l10n_latam_check_bank_id': self.l10n_latam_check_bank_id.id,
            'l10n_latam_check_issuer_vat': self.l10n_latam_check_issuer_vat,
            'check_number': self.l10n_latam_check_number,
            'l10n_latam_checkbook_id': self.l10n_latam_checkbook_id.id,
            'l10n_latam_check_payment_date': self.l10n_latam_check_payment_date,
        })
        return vals

    @api.onchange('l10n_latam_check_number')
    def _onchange_l10n_latam_check_number(self):
        for rec in self.filtered(lambda x: x.journal_id.company_id.country_id.code == "AR"):
            try:
                if rec.l10n_latam_check_number:
                    rec.l10n_latam_check_number = '%08d' % int(rec.l10n_latam_check_number)
            except Exception:
                pass
