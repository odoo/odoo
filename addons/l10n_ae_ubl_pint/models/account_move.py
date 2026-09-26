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
    _inherit = ['account.move', 'l10n.ae.pint.check.mixin']

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
            ('00010000', 'Summary'),
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
            # A document decoded from an incoming file carries the sender's own UUID (BTAE-02).
            # Deriving one from this database would overwrite the issuer's document identity,
            # so only generate when there is nothing to preserve.
            if move.l10n_ae_uuid:
                continue
            move.l10n_ae_uuid = str(uuid.uuid5(namespace=uuid.UUID(dbuuid), name=str(move.id)))
        return moves

    def _get_import_file_type(self, file_data):
        """ Identify PINT AE files. """
        # EXTENDS 'account_edi_ubl_cii'
        tree = file_data['xml_tree']
        # Both profiles AE publishes, see account.edi.xml.pint_ae's _get_customization_id.
        # Without the selfbilling one, incoming self-billed AE documents would fall through
        # to the generic UBLVersionID check in account_edi_ubl_cii and be decoded as plain UBL 2.1.
        if tree is not None and tree.findtext('{*}CustomizationID') in (
            'urn:peppol:pint:billing-1@ae-1',
            'urn:peppol:pint:selfbilling-1@ae-1',
        ):
            return 'account.edi.xml.pint_ae'

        return super()._get_import_file_type(file_data)

    def _l10n_ae_pint_group_by_error_code(self):
        self.ensure_one()
        # ibr-007-ae: Beneficiary ID (BTAE-01) MUST be provided for Free Trade Zone supplies.
        if self.l10n_ae_invoice_transaction_type == '10000000' and not self.l10n_ae_beneficiary_id:
            return (
                ("message", self.env._("Invoice(s) for a Free Trade Zone supply should have their Beneficiary ID set.")),
                ("error_code", "l10n_ae_pint_move_beneficiary_id_missing"),
                ("level", "danger"),
            )
        # ibr-137-ae: Principal ID (BTAE-14) MUST be provided for Disclosed Agent Billing.
        if self.l10n_ae_invoice_transaction_type == '00000100' and not self.l10n_ae_principal_id:
            return (
                ("message", self.env._("Invoice(s) for a Disclosed Agent Billing supply should have their Principal ID set.")),
                ("error_code", "l10n_ae_pint_move_principal_id_missing"),
                ("level", "danger"),
            )
        return False

    def _l10n_ae_pint_action_text(self):
        # EXTENDS 'l10n.ae.pint.check.mixin'
        return self.env._("View Invoice(s)")

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
