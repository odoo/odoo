
import uuid

from odoo import api, fields, models

CREDIT_NOTE_REASONS = [
    ('DL8.61.1.A', 'Supply was cancelled'),
    ('DL8.61.1.B', 'Tax treatment changed due to change in nature of supply'),
    ('DL8.61.1.C', 'Previously agreed consideration was altered (e.g. bad debt relief)'),
    ('DL8.61.1.D', 'Recipient returned goods or services in full or in part'),
    ('DL8.61.1.E', 'Tax was charged or tax treatment was applied in error'),
    ('VD', 'Volume Discount'),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ae_invoice_type = fields.Selection(
        string='AE Invoice Type',
        selection=[
            ('simplified', 'Simplified'),
            ('tax', 'Tax'),
            ('commercial', 'Commercial'),
        ],
        default='simplified',
    )
    l10n_ae_invoice_transaction_type = fields.Selection(
        string='AE Invoice Transaction Type',
        selection=[
            ('10000000', 'Free Trade Zone'),
            ('01000000', 'Deemed Supply'),
            ('00100000', 'Profit Margin Scheme'),
            ('00010000', 'Summary Invoice'),
            ('00001000', 'Continuous Supply'),
            ('00000100', 'Disclosed Agent Billing'),
            ('00000010', 'Supply through e-commerce'),
            ('00000001', 'Exports'),
        ],
    )
    l10n_ae_credit_note_reason = fields.Selection(string='AE Credit Note Reason', selection=CREDIT_NOTE_REASONS)
    l10n_ae_beneficiary_id = fields.Char(string='Beneficiary ID')
    l10n_ae_principal_id = fields.Char(string='Principal ID')
    l10n_ae_uuid = fields.Char(string='AE PINT UUID', copy=False)
    l10n_ae_card_number = fields.Char(string='AE Card Number (masked)')
    l10n_ae_card_network = fields.Char(string='AE Card Network')

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        # AE Pint requires us to generate a uuid, derived from the dbuuid and the move id
        # so it stays stable.
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        for move in moves:
            move.l10n_ae_uuid = str(uuid.uuid5(namespace=uuid.UUID(dbuuid), name=str(move.id)))
        return moves

    def _group_by_error_code(self):
        self.ensure_one()
        # ibr-007-ae: Beneficiary ID (BTAE-01) MUST be provided for Free Trade Zone supplies.
        if self.l10n_ae_invoice_transaction_type == '10000000' and not self.l10n_ae_beneficiary_id:
            return (
                ("message", self.env._("Invoice(s) for a Free Trade Zone supply should have their Beneficiary ID set.")),
                ("error_code", "l10n_ae_ubl_pint_move_beneficiary_id_missing"),
                ("level", "danger"),
            )
        # ibr-137-ae: Principal ID (BTAE-14) MUST be provided for Disclosed Agent Billing.
        if self.l10n_ae_invoice_transaction_type == '00000100' and not self.l10n_ae_principal_id:
            return (
                ("message", self.env._("Invoice(s) for a Disclosed Agent Billing supply should have their Principal ID set.")),
                ("error_code", "l10n_ae_ubl_pint_move_principal_id_missing"),
                ("level", "danger"),
            )
        return False

    def _l10n_ae_ubl_pint_export_check(self):
        """Validate Invoice for PINT AE compliance."""
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            alert_vals.update(
                {
                    temp_dict["error_code"]: {
                        "message": temp_dict["message"],
                        "level": temp_dict["level"],
                        "action": invalid_records._get_records_action(),
                        "action_text": self.env._("View Invoice(s)"),
                    },
                },
            )
        return alert_vals

    def l10n_ae_get_payment_means_details(self):
        """Derives the UNCL4461 payment means code/name from the invoice's own standard payment
        method data - preferred_payment_method_line_id (account's own standard "how will this be
        paid" field, computed from the partner's inbound/outbound payment method) tells us cash
        vs. bank via its journal. Debit card is the one exception: nothing standard on the
        invoice signals it, so it's inferred from the card fields actually being filled in.
        """
        self.ensure_one()
        if self.l10n_ae_card_number and self.l10n_ae_card_network:
            return 55, 'Debit card'
        payment_method_line = self.preferred_payment_method_line_id
        if payment_method_line.journal_id.type == 'cash':
            return 10, 'In cash'
        if payment_method_line.journal_id.type == 'bank' or self.partner_bank_id:
            return 30, 'Credit transfer'
        return 1, 'Instrument not defined'
