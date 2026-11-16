# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_si_upn_qr_purpose_code = fields.Selection(
        selection=[
            ('GDSV', "GDSV - Goods and services"),
            ('GDDS', "GDDS - Goods"),
            ('SCVE', "SCVE - Services"),
            ('ADVA', "ADVA - Advance payment"),
            ('RENT', "RENT - Rent"),
            ('SUBS', "SUBS - Subscription"),
            ('CHAR', "CHAR - Charity payment"),
            ('OTHR', "OTHR - Other"),
        ],
        string="Purpose Code",
        default='GDSV',
        help="Purpose of the payment, written in the UPN QR code of the invoice.",
    )
    l10n_si_show_upn_qr_purpose_code = fields.Boolean(compute='_compute_l10n_si_show_upn_qr_purpose_code')

    @api.depends('display_qr_code', 'country_code', 'partner_bank_id', 'partner_id.country_id', 'currency_id')
    def _compute_l10n_si_show_upn_qr_purpose_code(self):
        for move in self:
            # Not _get_qr_code_method() as it gives nothing while there is nothing to pay,
            # which would hide the field on a new invoice and we don't want that.
            move.l10n_si_show_upn_qr_purpose_code = (
                move.display_qr_code
                and move.country_code == 'SI'
                and not move.partner_bank_id._get_error_messages_for_qr('si_upn_qr', move.partner_id, move.currency_id)
            )

    def _generate_qr_code(self, silent_errors=False):
        """ Pass along the data a UPN QR code holds but the generic QR-code
        generation signature does not provide.
        """
        # EXTENDS account
        self.ensure_one()
        return super(AccountMove, self.with_context(
            l10n_si_upn_qr_payment_deadline=self.invoice_date_due,
            l10n_si_upn_qr_payment_purpose=self.name,
            l10n_si_upn_qr_purpose_code=self.l10n_si_upn_qr_purpose_code,
        ))._generate_qr_code(silent_errors)

    @api.depends('country_code')
    def _compute_show_taxable_supply_date(self):
        super()._compute_show_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'SI' and m.move_type != 'entry' and (m.state == 'draft' or m.taxable_supply_date)):
            move.show_taxable_supply_date = True

    @api.depends('country_code')
    def _compute_taxable_supply_date_placeholder(self):
        super()._compute_taxable_supply_date_placeholder()
        for move in self.filtered(lambda m: m.country_code == 'SI'):
            move.taxable_supply_date_placeholder = self.env._("Invoice Date")

    def _get_accounting_date_source(self):
        return (self.country_code == 'SI' and self.taxable_supply_date) or super()._get_accounting_date_source()

    def _get_invoice_currency_rate_date(self):
        return (self.country_code == 'SI' and self.taxable_supply_date) or super()._get_invoice_currency_rate_date()

    def _get_default_currency_rate_date(self):
        return (self.country_code == 'SI' and self.taxable_supply_date) or super()._get_default_currency_rate_date()

    def _get_invoice_reference_si_partner(self):
        """
        Generate the Slovenian structured payment reference using the partner's ID.
        Format: SI01 (P1-P2-P3)K
        - P1: Last two digits of the invoice year
        - P2: Partner ID
        - P3: Journal ID
        - K: Check digit

        :return: the formatted structured reference string (SI01...)
        """
        self.ensure_one()
        p3 = str(self.partner_id.id)
        return self._build_invoice_reference(p3)

    def _get_invoice_reference_si_invoice(self):
        """
        Generate the Slovenian structured payment reference using the invoice sequence number.

        Format: SI01 (P1-P2-P3)K
        - P1: Last two digits of the invoice year
        - P2: Trailing digits of the invoice name (sequence number)
        - P3: Journal ID
        - K: Check digit

        :return: the formatted structured reference string (SI01...)
        """
        self.ensure_one()
        match = re.search(r'(\d+)$', self.name or '')
        p3 = str(int(match.group(1))) if match else '0'
        return self._build_invoice_reference(p3)

    def _build_invoice_reference(self, p3):
        """Builds the reference using a shared structure for both methods."""
        p1 = str(self.journal_id.id)
        p2 = str(self.invoice_date.year)[-2:]
        reference_base = f"{p1}-{p2}-{p3}"

        # Calculate check digit
        digits = [int(d) for d in reference_base if d.isdigit()]
        weights = list(range(2, 14))[:len(digits)]
        weighted_sum = sum(d * w for d, w in zip(reversed(digits), weights))
        check_digit = 11 - (weighted_sum % 11)
        check_digit = 0 if check_digit in (10, 11) else check_digit
        return f"SI01 {reference_base}{check_digit}"
