from collections import defaultdict

from odoo import api, fields, models


class L10nPlAccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_pl_verification_id = fields.Many2one(
        string='PL Bank Verification',
        comodel_name='l10n_pl.bank.account.verification',
        compute='_compute_l10n_pl_verification_id',
        store=True,
        readonly=True,
        copy=False,
    )
    l10n_pl_verification_status = fields.Selection(related='l10n_pl_verification_id.verification_status')
    l10n_pl_verification_timestamp = fields.Datetime(related='l10n_pl_verification_id.verification_timestamp')
    l10n_pl_verification_request_id = fields.Char(related='l10n_pl_verification_id.verification_request_id')

    @api.model
    def _payment_need_check(self, partner, payment_type, amounts, currency):
        """
        :param amounts: list of amounts in case values are coming from a batch
        """
        return (
            partner.country_code == 'PL'
            and payment_type == 'outbound'
            and any(currency.compare_amounts(amount, 15000) >= 0 for amount in amounts)
            and currency.name == 'PLN'
        )

    @api.depends('state', 'date', 'partner_id', 'partner_bank_id')
    def _compute_l10n_pl_verification_id(self):
        partner_to_partner_banks = defaultdict(self.env['res.partner.bank'].browse)  # {partner: recordset(res.partner.bank)}
        for pay in self:
            if pay.state == 'draft':
                pay.l10n_pl_verification_id = False
                continue
            elif pay.company_id.country_code != 'PL':
                continue

            partner = pay.partner_id
            if not partner or not self._payment_need_check(partner, pay.payment_type, [pay.amount], pay.currency_id):
                continue

            partner_bank = pay.partner_bank_id or partner.bank_ids[:1]
            if not partner_bank:
                partner_to_partner_banks[partner.id] |= partner_bank
                continue

            partner_to_partner_banks[partner.id] |= partner_bank

        partner_bank_data = list(partner_to_partner_banks.items())
        date = fields.Date.context_today(self.with_context(tz='Europe/Warsaw'))
        verifications = self.env['l10n_pl.bank.account.verification']._l10n_pl_get_verification(partner_bank_data, date)
        bank2verification = verifications.grouped('partner_bank_account_number')
        partner2verification = verifications.grouped('partner_vat')

        for pay in self:
            partner = pay.partner_id
            if not partner:
                continue

            partner_bank = pay.partner_bank_id or partner.bank_ids[:1]
            if partner_bank:
                pay.l10n_pl_verification_id = bank2verification.get(partner_bank.sanitized_account_number)
            else:
                pay.l10n_pl_verification_id = partner2verification.get(partner.vat)
