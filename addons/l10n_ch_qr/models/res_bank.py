# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.base_iban.models.res_partner_bank import normalize_iban, pretty_iban, validate_iban
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.exceptions import ValidationError

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_ch_qr_iban = fields.Char(string='QR-IBAN')

    def _validate_ch_qr_iban(self, qr_iban):
        # Check first if it's a valid IBAN.
        validate_iban(qr_iban)
        # We sanitize first so that _validate_qr_iban() can extract correct IID from IBAN to validate it.
        sanitized_qr_iban = sanitize_account_number(qr_iban)
        # Now, check if it's valid QR-IBAN (based on its IID).
        if not self._validate_qr_iban(sanitized_qr_iban):
            raise ValidationError(_("QR-IBAN '%s' is invalid.") % qr_iban)
        return True

    @api.onchange('acc_type')
    def _onchange_reset_ch_qr_iban(self):
        if self.acc_type != 'iban':
            self.l10n_ch_qr_iban = False

    @api.model
    def create(self, vals):
        if vals.get('l10n_ch_qr_iban'):
            self._validate_ch_qr_iban(vals['l10n_ch_qr_iban'])
            vals['l10n_ch_qr_iban'] = pretty_iban(normalize_iban(vals['l10n_ch_qr_iban']))
        return super().create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('l10n_ch_qr_iban'):
            self._validate_ch_qr_iban(vals['l10n_ch_qr_iban'])
            vals['l10n_ch_qr_iban'] = pretty_iban(normalize_iban(vals['l10n_ch_qr_iban']))
        return super().write(vals)

    def _is_qr_iban(self):
        res = super()._is_qr_iban()
        try:
            # If the acc_number is valid QR-IBAN, we will use acc_number to build SWISS code URL.
            if not res and self.l10n_ch_qr_iban:
                res = self._validate_ch_qr_iban(self.l10n_ch_qr_iban)
        except ValidationError:
            pass
        return res

    def _prepare_swiss_code_url_vals(self, amount, currency_name, debtor_partner, reference_type, reference, comment):
        qr_code_vals = super()._prepare_swiss_code_url_vals(amount, currency_name, debtor_partner, reference_type, reference, comment)
        try:
            # If the acc_number is IBAN but not QR-IBAN and if l10n_ch_qr_iban (QR-IBAN) is set,
            # we ensure l10n_ch_qr_iban has a valid QR-IBAN and we use it to build SWISS code URL.
            if not self._validate_qr_iban(self.sanitized_acc_number) \
                    and self.l10n_ch_qr_iban and self._validate_ch_qr_iban(self.l10n_ch_qr_iban):
                qr_code_vals[3] = sanitize_account_number(self.l10n_ch_qr_iban)
        except ValidationError:
            pass
        return qr_code_vals
