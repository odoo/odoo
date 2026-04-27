# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    bacs_ddi_usable = fields.Boolean(string="Could a SDD ddi be used?",
        compute='_compute_usable_ddi')
    bacs_payment_type = fields.Selection(selection=[
        ('dd_sub_init', 'Direct debit-first collection of a series'),
        ('dd_regular', 'Direct debit single collection'),
        ('dd_sub_rep', 'Direct debit repeating collection in a series'),
        ('dd_sub_fin', 'Direct debit-final collection of a series'),
    ], string="BACS Payment Type", default='dd_regular', required=True)
    bacs_ddi_id = fields.Many2one(
        comodel_name='bacs.ddi',
        copy=False,
    )

    def write(self, vals):
        # OVERRIDE
        # Register BACS Direct Debit payments on DDIs or trigger an error if no DDI is available.
        draft_bacs = self.filtered(lambda p: p.payment_method_code == 'bacs_dd' and p.state == 'draft')
        res = super().write(vals)
        for pay in draft_bacs.filtered(lambda p: p.state == 'in_process'):
            usable_ddi = pay.get_usable_ddi()
            if not usable_ddi:
                raise UserError(_(
                    "Unable to post payment “%(payment)s” because there are no usable DDI that are available at date %(date)s for partner “%(partner)s”. Please create one before encoding a BACS Direct Debit payment.",
                    payment=pay.name,
                    date=pay.date,
                    partner=pay.partner_id.name,
                ))
            pay.bacs_ddi_id = usable_ddi
        return res

    @api.model
    def _get_method_codes_using_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_using_bank_account()
        res += ['bacs_dc']
        return res

    @api.model
    def _get_method_codes_needing_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_needing_bank_account()
        res += ['bacs_dc']
        return res

    @api.constrains('payment_method_line_id', 'journal_id', 'partner_bank_id')
    def _check_bacs_bank_account(self):
        bacs_dc_payment_method = self.env.ref('l10n_uk_bacs.payment_method_bacs_dc')
        bacs_dd_payment_method = self.env.ref('l10n_uk_bacs.payment_method_bacs_dd')
        for rec in self:
            if rec.payment_method_id in (bacs_dc_payment_method, bacs_dd_payment_method):
                if not rec.journal_id.bank_account_id or rec.journal_id.bank_account_id.acc_type != 'iban' or rec.journal_id.bank_account_id.acc_number[:2] != 'GB':
                    raise ValidationError(_("The journal '%s' requires a proper IBAN account to initiate a BACS Payment. Please configure it first.", rec.journal_id.name))
                if rec.payment_method_id == bacs_dc_payment_method and (rec.partner_bank_id.acc_type != 'iban' or rec.partner_bank_id.sanitized_acc_number[:2].upper() != 'GB'):
                    raise ValidationError(_("The selected vendor account needs to be a valid UK IBAN"))

    def _get_payment_method_codes_to_exclude(self):
        res = super()._get_payment_method_codes_to_exclude()
        gbp_currency_id = self.env.ref('base.GBP')
        bacs_dc = self.env.ref('l10n_uk_bacs.payment_method_bacs_dc', raise_if_not_found=False)
        bacs_dd = self.env.ref('l10n_uk_bacs.payment_method_bacs_dd', raise_if_not_found=False)
        if self.currency_id != gbp_currency_id:
            if bacs_dc:
                res.append(bacs_dc.code)
            if bacs_dd:
                res.append(bacs_dd.code)
        return res


    @api.depends('date', 'partner_id', 'company_id')
    def _compute_usable_ddi(self):
        """ returns wether this payment has a usable ddi or not.
        """
        for payment in self:
            payment.bacs_ddi_usable = bool(payment.get_usable_ddi())

    def get_usable_ddi(self):
        """ Returns the sdd ddi that can be used to generate this payment, or
        None if there is none.
        """

        return self.env['bacs.ddi']._bacs_get_usable_ddi(
            self.company_id.id or self.env.company.id,
            self.partner_id.commercial_partner_id.id,
            self.date)
