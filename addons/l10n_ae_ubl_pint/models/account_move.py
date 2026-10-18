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
        compute='_compute_l10n_ae_invoice_type',
        store=True,
        readonly=False,
        copy=True,
    )
    l10n_ae_transaction_type_ids = fields.Many2many(
        comodel_name='l10n_ae.transaction.type',
        string='AE Transaction Types',
        compute='_compute_l10n_ae_transaction_type_ids',
        store=True,
        readonly=False,
        copy=True,
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

    def _l10n_ae_is_sent_by_peppol(self):
        """ A simplified invoice or credit note of a UAE company isn't sent by Peppol. """
        self.ensure_one()
        return not (
            self.country_code == 'AE'
            and self.move_type in ('out_invoice', 'out_refund')
            and self.l10n_ae_invoice_type == 'simplified'
        )

    @api.depends('fiscal_position_id')
    def _compute_l10n_ae_transaction_type_ids(self):
        """ A draft under a fiscal position that isn't for the UAE is an export by default.

        Only added, never removed: the user may have set the types on purpose.
        """
        exports = self.env.ref('l10n_ae_ubl_pint.transaction_type_exports', raise_if_not_found=False)
        for move in self:
            transaction_types = move.l10n_ae_transaction_type_ids
            if (
                exports
                and move.country_code == 'AE'
                and move.state == 'draft'
                and move.move_type in ('out_invoice', 'out_refund')
                and move._l10n_ae_is_foreign_fiscal_position()
            ):
                transaction_types |= exports
            move.l10n_ae_transaction_type_ids = transaction_types

    def _l10n_ae_is_foreign_fiscal_position(self):
        """ Whether the fiscal position is set and isn't for the United Arab Emirates. """
        self.ensure_one()
        fiscal_position = self.fiscal_position_id
        return bool(fiscal_position) and not (
            fiscal_position.country_id.code == 'AE'
            or 'AE' in fiscal_position.country_group_id.country_ids.mapped('code')
        )

    def _l10n_ae_has_transaction_type(self, code):
        """ Whether the transaction type with this code (e.g. '00000001' for Exports) applies. """
        self.ensure_one()
        return code in self.l10n_ae_transaction_type_ids.mapped('code')

    @api.depends('partner_id', 'country_code')
    def _compute_l10n_ae_invoice_type(self):
        """ A tax invoice for a company, a simplified one for an individual, on drafts only. """
        for move in self:
            if move.country_code != 'AE':
                move.l10n_ae_invoice_type = False
            elif move.state == 'draft' or not move.l10n_ae_invoice_type:
                move.l10n_ae_invoice_type = 'tax' if move.partner_id.commercial_partner_id.is_company else 'simplified'
            else:
                move.l10n_ae_invoice_type = move.l10n_ae_invoice_type

    @api.depends('country_code')
    def _compute_l10n_ae_uuid(self):
        """ BTAE-07, stored to stay the same across sends. An imported document keeps the issuer's. """
        for move in self:
            if not move.l10n_ae_uuid and move.country_code == 'AE':
                move.l10n_ae_uuid = str(uuid.uuid4())

    def _get_import_file_type(self, file_data):
        """ Identify PINT AE files, billing and self-billing ones. """
        # EXTENDS 'account_edi_ubl_cii'
        tree = file_data['xml_tree']
        if tree is not None and tree.findtext('{*}CustomizationID') in (
            'urn:peppol:pint:billing-1@ae-1',
            'urn:peppol:pint:selfbilling-1@ae-1',
        ):
            return 'account.edi.xml.pint_ae'

        return super()._get_import_file_type(file_data)

    def _l10n_ae_pint_group_by_error_code(self):
        """ The PINT AE rules on the invoice's own data.

        - ibr-007-ae: Beneficiary ID (BTAE-01) for a Free Trade Zone supply.
        - ibr-137-ae: Principal ID (BTAE-14) for a Disclosed Agent Billing.
        - ibr-160-ae: an "Others" billing frequency is described in the note (IBT-022), built
          from the Terms & Conditions.
        - ibr-158-ae: Credit note reason code (BTAE-03) on a tax credit note.
        - ibr-055-ae: a credit note references the invoice it credits, unless its reason is
          Volume Discount.
        """
        self.ensure_one()
        if self._l10n_ae_has_transaction_type('10000000') and not self.l10n_ae_beneficiary_id:
            return (
                ("message", self.env._("Invoice(s) for a Free Trade Zone supply should have their Beneficiary ID set.")),
                ("error_code", "l10n_ae_pint_move_beneficiary_id_missing"),
                ("level", "danger"),
            )
        if self._l10n_ae_has_transaction_type('00000100') and not self.l10n_ae_principal_id:
            return (
                ("message", self.env._("Invoice(s) for a Disclosed Agent Billing supply should have their Principal ID set.")),
                ("error_code", "l10n_ae_pint_move_principal_id_missing"),
                ("level", "danger"),
            )
        if self.invoice_payment_term_id.l10n_ae_billing_frequency == 'OTH' and is_html_empty(self.narration):
            return (
                ("message", self.env._(
                    "Invoice(s) with an \"Others\" billing frequency should describe it in their Terms & Conditions.",
                )),
                ("error_code", "l10n_ae_pint_move_billing_frequency_note_missing"),
                ("level", "danger"),
            )
        if self._l10n_ae_is_credit_note():
            is_commercial = self.l10n_ae_invoice_type == 'commercial'
            if not is_commercial and not self.l10n_ae_credit_note_reason:
                return (
                    ("message", self.env._("Credit note(s) should have their Credit Note Reason set.")),
                    ("error_code", "l10n_ae_pint_move_credit_note_reason_missing"),
                    ("level", "danger"),
                )
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
        """ Whether this move is exported as a PINT AE credit note, self-billed ones included. """
        self.ensure_one()
        return self.move_type == 'out_refund' or (self.move_type == 'in_refund' and self.l10n_ae_is_self_billing)

    def _l10n_ae_get_preceding_invoices(self):
        """ The preceding invoices (IBG-03) the export references: the reconciled ones, else the reversed one. """
        self.ensure_one()
        receivable_lines = self.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')

        def named(moves):
            return moves.filtered(lambda move: move.name and move.name != '/')

        return named(receivable_lines.matched_credit_ids.credit_move_id.move_id) or named(self.reversed_entry_id)

    def _l10n_ae_pint_action_text(self):
        # EXTENDS 'l10n.ae.pint.check.mixin'
        return self.env._("View Invoice(s)")

    def l10n_ae_get_payment_means_details(self):
        """ The UNCL4461 payment means code and name, from the preferred payment method's journal. """
        self.ensure_one()
        payment_method_line = self.preferred_payment_method_line_id
        if payment_method_line.journal_id.type == 'cash':
            return 10, 'In cash'
        if payment_method_line.journal_id.type == 'bank' or self.partner_bank_id:
            return 30, 'Credit transfer'
        return 1, 'Instrument not defined'
