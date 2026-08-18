from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


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

    def _auto_init(self):
        if not column_exists(self.env.cr, 'account_payment', 'l10n_pl_verification_id'):
            create_column(self.env.cr, 'account_payment', 'l10n_pl_verification_id', 'integer')
        super()._auto_init()

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
        partner_to_partner_banks = defaultdict(list)  # {partner: [res.partner.bank]}
        for pay in self:
            if pay.state == 'draft':
                pay.l10n_pl_verification_id = False
                continue
            elif pay.company_id.country_code != 'PL':
                continue

            partner = pay.partner_id
            if not partner or not self._payment_need_check(partner, pay.payment_type, [pay.amount], pay.currency_id):
                continue

            partner_bank = pay.partner_bank_id
            partner_to_partner_banks[partner.id].append(partner_bank)

        partner_bank_data = list(partner_to_partner_banks.items())
        date = fields.Date.context_today(self.with_context(tz='Europe/Warsaw'))
        verifications = self.env['l10n_pl.bank.account.verification']._l10n_pl_get_verification(partner_bank_data, date)
        partner_and_bank2verifications = verifications.grouped(lambda v: (v.partner_id, v.partner_bank_id.sanitized_acc_number))

        for pay in self:
            partner = pay.partner_id
            if not partner:
                pay.l10n_pl_verification_id = False
            elif partner_bank := pay.partner_bank_id:
                pay.l10n_pl_verification_id = partner_and_bank2verifications.get(
                    (partner, partner_bank.sanitized_acc_number),
                    partner_and_bank2verifications.get((partner, False))  # default getter for partners with no vat
                )
            else:
                pay.l10n_pl_verification_id = partner_and_bank2verifications.get((partner, False))
