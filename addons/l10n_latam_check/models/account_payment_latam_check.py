import stdnum

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date


class AccountPaymentLatamCheck(models.Model):
    _name = 'account.payment.latam.check'
    _description = 'latam check'
    _check_company_auto = True

    payment_id = fields.Many2one(
        comodel_name='account.payment',
    )
    l10n_latam_check_number = fields.Char(
    )
    # New third party check info
    l10n_latam_check_bank_id = fields.Many2one(
        comodel_name='res.bank',
        string='Check Bank',
        compute='_compute_l10n_latam_check_bank_id', store=True, readonly=False,
    )
    l10n_latam_check_issuer_vat = fields.Char(
        string='Check Issuer VAT',
        compute='_compute_l10n_latam_check_issuer_vat', store=True, readonly=False,
    )
    l10n_latam_check_payment_date = fields.Date(
        string='Check Cash-In Date',
        help="Date from when you can cash in the check, turn the check into cash",
        readonly=False,
    )
    currency_id = fields.Many2one(related="payment_id.currency_id")
    amount = fields.Monetary()

    @api.depends('payment_id.payment_method_line_id.code', 'payment_id.partner_id')
    def _compute_l10n_latam_check_bank_id(self):
        new_third_party_checks = self.payment_id.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
        for rec in new_third_party_checks:
            rec.l10n_latam_check_bank_id = rec.partner_id.bank_ids[:1].bank_id
        (self - new_third_party_checks).l10n_latam_check_bank_id = False

    @api.depends('payment_id.payment_method_line_id.code', 'payment_id.partner_id')
    def _compute_l10n_latam_check_issuer_vat(self):
        new_third_party_checks = self.payment_id.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
        for rec in new_third_party_checks:
            rec.l10n_latam_check_issuer_vat = rec.partner_id.vat
        (self - new_third_party_checks).l10n_latam_check_issuer_vat = False

    # @api.onchange('l10n_latam_check_issuer_vat')
    # def _clean_l10n_latam_check_issuer_vat(self):
    #     for rec in self.filtered(lambda x: x.l10n_latam_check_issuer_vat and x.company_id.country_id.code):
    #         stdnum_vat = stdnum.util.get_cc_module(rec.company_id.country_id.code, 'vat')
    #         if hasattr(stdnum_vat, 'compact'):
    #             rec.l10n_latam_check_issuer_vat = stdnum_vat.compact(rec.l10n_latam_check_issuer_vat)

    # @api.constrains('l10n_latam_check_issuer_vat', 'company_id')
    # def _check_l10n_latam_check_issuer_vat(self):
    #     for rec in self.filtered(lambda x: x.l10n_latam_check_issuer_vat and x.company_id.country_id):
    #         if not self.env['res.partner']._run_vat_test(rec.l10n_latam_check_issuer_vat, rec.company_id.country_id):
    #             error_message = self.env['res.partner']._build_vat_error_message(
    #                 rec.company_id.country_id.code.lower(), rec.l10n_latam_check_issuer_vat, 'Check Issuer VAT')
    #             raise ValidationError(error_message)