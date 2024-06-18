# pylint: disable=protected-access
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api
import stdnum

_logger = logging.getLogger(__name__)


class l10nLatamCheckPaymentRegisterCheck(models.TransientModel):
    _name = 'l10n_latam.payment.register.check'
    _description = 'Payment register check'
    _check_company_auto = True

    payment_register_id = fields.Many2one('account.payment.register', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='payment_register_id.company_id')
    currency_id = fields.Many2one(related='payment_register_id.currency_id')
    name = fields.Char(string='Number')
    bank_id = fields.Many2one(
        comodel_name='res.bank',
        compute='_compute_bank_id', store=True, readonly=False,
    )
    issuer_vat = fields.Char(
        compute='_compute_issuer_vat', store=True, readonly=False,
    )
    payment_date = fields.Date(readonly=False, required=True)
    amount = fields.Monetary()

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            self.name = self.name.zfill(8)

    @api.depends('payment_register_id.payment_method_line_id.code', 'payment_register_id.partner_id')
    def _compute_bank_id(self):
        new_third_party_checks = self.filtered(lambda x: x.payment_register_id.payment_method_line_id.code == 'new_third_party_checks')
        for rec in new_third_party_checks:
            rec.bank_id = rec.payment_register_id.partner_id.bank_ids[:1].bank_id
        (self - new_third_party_checks).bank_id = False

    @api.depends('payment_register_id.payment_method_line_id.code', 'payment_register_id.partner_id')
    def _compute_issuer_vat(self):
        new_third_party_checks = self.filtered(lambda x: x.payment_register_id.payment_method_line_id.code == 'new_third_party_checks')
        for rec in new_third_party_checks:
            rec.issuer_vat = rec.payment_register_id.partner_id.vat
        (self - new_third_party_checks).issuer_vat = False

    @api.onchange('issuer_vat')
    def _clean_issuer_vat(self):
        for rec in self.filtered(lambda x: x.issuer_vat and x.company_id.country_id.code):
            stdnum_vat = stdnum.util.get_cc_module(rec.company_id.country_id.code, 'vat')
            if hasattr(stdnum_vat, 'compact'):
                rec.issuer_vat = stdnum_vat.compact(rec.issuer_vat)
