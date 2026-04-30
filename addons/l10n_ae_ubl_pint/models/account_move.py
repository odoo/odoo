import uuid

from odoo import api, fields, models
from odoo.tools import is_html_empty

CREDIT_NOTE_REASONS = [
    ('DL8.61.1.A', 'Supply was cancelled'),
    ('DL8.61.1.B', 'Tax treatment changed due to change in nature of supply'),
    ('DL8.61.1.C', 'Previously agreed consideration was altered (e.g. bad debt relief)'),
    ('DL8.61.1.D', 'Recipient returned goods or services in full or in part'),
    ('DL8.61.1.E', 'Tax was charged or tax treatment was applied in error'),
    ('VD', 'Volume Discount'),
]


class AccountMove(models.Model):
    _name = 'account.move'
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
    l10n_ae_is_self_billing = fields.Boolean(related='journal_id.is_self_billing')
    # Editable on credit notes as their preceding invoice reference, see the view.
    reversed_entry_id = fields.Many2one(tracking=True)
    l10n_ae_beneficiary_id = fields.Char(string='Beneficiary ID')
    l10n_ae_principal_id = fields.Char(string='Principal ID')
    l10n_ae_uuid = fields.Char(
        string='AE PINT UUID',
        compute='_compute_l10n_ae_uuid',
        store=True,
        readonly=False,
        copy=False,
    )
    l10n_ae_card_number = fields.Char(string='AE Card Number (masked)')
    l10n_ae_card_network = fields.Char(string='AE Card Network')

    @api.depends('country_code')
    def _compute_l10n_ae_uuid(self):
        # BTAE-02 must stay the same across every send of a document, which storing it guarantees.
        # An already set value is kept: a document decoded from an incoming file carries the
        # issuer's own UUID.
        for move in self:
            if not move.l10n_ae_uuid and move.country_code == 'AE':
                move.l10n_ae_uuid = str(uuid.uuid4())

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
        if self.invoice_payment_term_id.l10n_ae_billing_frequency == 'OTH' and is_html_empty(self.narration):
            # [ibr-160-ae] The invoice note (IBT-022) is built from the Terms & Conditions.
            return (
                ("message", self.env._(
                    "Invoice(s) with an \"Others\" billing frequency should describe it in their Terms & Conditions.",
                )),
                ("error_code", "l10n_ae_pint_move_billing_frequency_note_missing"),
                ("level", "danger"),
            )
        if self._l10n_ae_is_credit_note():
            is_commercial = self.l10n_ae_invoice_type == 'commercial'
            # ibr-158-ae: a credit note (381) MUST carry its Credit note reason code (BTAE-03).
            # https://docs.peppol.eu/poac/ae/pint-ae/trn-creditnote/semantic-model/btae-03/
            if not is_commercial and not self.l10n_ae_credit_note_reason:
                return (
                    ("message", self.env._("Credit note(s) should have their Credit Note Reason set.")),
                    ("error_code", "l10n_ae_pint_move_credit_note_reason_missing"),
                    ("level", "danger"),
                )
            # ibr-055-ae: a credit note (381/81) MUST reference the invoice it credits, unless its
            # reason is Volume Discount.
            # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-055-ae/
            if self.l10n_ae_credit_note_reason != 'VD' and not self._l10n_ae_get_preceding_invoices():
                return (
                    ("message", self.env._(
                        "Credit note(s) should be linked to the invoice they credit: create them with "
                        "\"Credit Note\" from the invoice, set the invoice in \"Reversal Of\" (Other Info "
                        "tab, FTA section), or use the Volume Discount reason.",
                    )),
                    ("error_code", "l10n_ae_pint_move_preceding_invoice_missing"),
                    ("level", "danger"),
                )
        return False

    def _l10n_ae_is_credit_note(self):
        """Whether this move is exported as a PINT AE credit note, self-billed ones included."""
        self.ensure_one()
        return self.move_type == 'out_refund' or (self.move_type == 'in_refund' and self.l10n_ae_is_self_billing)

    def _l10n_ae_get_preceding_invoices(self):
        """The invoices the exporter references as preceding invoices (IBG-03) of this credit note.

        Those reconciled with it (account.edi.ubl_pint's _ubl_add_billing_reference_nodes) and, as a
        fallback, the reversed one (account.edi.xml.pint_ae's _ubl_add_billing_reference_nodes).
        """
        self.ensure_one()
        receivable_lines = self.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')

        def named(moves):
            return moves.filtered(lambda move: move.name and move.name != '/')

        return named(receivable_lines.matched_credit_ids.credit_move_id.move_id) or named(self.reversed_entry_id)

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
