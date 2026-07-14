from collections import defaultdict

from odoo import api, fields, models


class L10nPlAccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # partners for whose link between vat and bank account is validated by gov api
    l10n_pl_bank_verification_ids = fields.Many2many(comodel_name='l10n_pl.bank.account.verification', compute='_compute_l10n_pl_bank_verification')
    # partners for whose we cannot find link between vat and bank account calling gov api
    l10n_pl_bank_verification_invalid_bank_account_ids = fields.Many2many(comodel_name='res.partner.bank', compute='_compute_l10n_pl_bank_verification')
    # partners whose vat cannot be found in gov api
    l10n_pl_not_found_partner_ids = fields.Many2many(comodel_name='res.partner', compute='_compute_l10n_pl_bank_verification')
    # partners who do not have a VAT number or bank account (-> internal, no api call)
    l10n_pl_incomplete_data_partner_ids = fields.Many2many(comodel_name='res.partner', compute='_compute_l10n_pl_bank_verification')

    @api.depends('line_ids', 'partner_bank_id')
    def _compute_l10n_pl_bank_verification(self):
        date = fields.Date.context_today(self.with_context(tz='Europe/Warsaw'))
        for wizard in self:
            # Early skip if company not PL
            if wizard.company_id.country_code != 'PL':
                wizard.l10n_pl_bank_verification_ids = False
                wizard.l10n_pl_bank_verification_invalid_bank_account_ids = False
                wizard.l10n_pl_not_found_partner_ids = False
                wizard.l10n_pl_incomplete_data_partner_ids = False
                continue

            partner_to_partner_banks = defaultdict(self.env['res.partner.bank'].browse)  # {partner: recordset(res.partner.bank)}
            for batch in wizard.batches:
                if self._batch_need_check(batch):
                    partner_to_partner_banks[batch['payment_values']['partner_id']] |= self._get_partner_bank_from_batch(batch)

            partner_bank_data = [(partner_id, partner_banks) for partner_id, partner_banks in partner_to_partner_banks.items()]
            verifications = self.env['l10n_pl.bank.account.verification']._l10n_pl_get_verification(partner_bank_data, date)
            wizard.l10n_pl_bank_verification_ids = verifications
            wizard.l10n_pl_bank_verification_invalid_bank_account_ids = verifications.filtered(
                lambda verif: verif.verification_status == 'invalid'
            ).partner_bank_id
            wizard.l10n_pl_not_found_partner_ids = verifications.filtered(
                lambda verif: verif.verification_status == 'not_found_partner'
            ).partner_id
            wizard.l10n_pl_incomplete_data_partner_ids = verifications.filtered(
                lambda verif: verif.verification_status == 'incomplete_partner'
            ).partner_id

    @api.model
    def _batch_need_check(self, batch):
        """
        Does batch need a government API call to check if the partner vat is linked to its account number
        """
        partner = self.env['res.partner'].browse(batch['payment_values']['partner_id'])
        if isinstance(batch['lines'], models.Model):
            moves = batch['lines'].move_id
        else:
            moves = self.env['account.move.line'].browse(batch['lines']).move_id

        return self.env['account.payment']._payment_need_check(
            partner,
            batch['payment_values']['payment_type'],
            moves.mapped('amount_total'),
            moves.currency_id,
        )

    def _create_payment_vals_from_wizard(self, batch_result):
        # EXTENDS account
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        return self._update_payment_vals(payment_vals, batch_result)

    def _create_payment_vals_from_batch(self, batch_result):
        # EXTENDS account
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        return self._update_payment_vals(payment_vals, batch_result)

    # ===================================
    # HELPERS
    # ===================================

    def _update_payment_vals(self, payment_vals, batch_result):
        if not self._batch_need_check(batch_result):
            return payment_vals

        partner_bank = self._get_partner_bank_from_batch(batch_result)
        verification = self.l10n_pl_bank_verification_ids.filtered(
            lambda verif: verif.partner_bank_id == partner_bank
        )
        payment_vals.update({
            'l10n_pl_verification_id': verification.id,
        })

        return payment_vals

    @api.model
    def _get_partner_bank_from_batch(self, batch):
        if partner_bank_id := batch['payment_values']['partner_bank_id']:
            return self.env['res.partner.bank'].browse(partner_bank_id)
        partner = self.env['res.partner'].browse(batch['payment_values']['partner_id'])
        return partner.bank_ids[:1]
