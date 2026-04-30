import uuid

from odoo import api, fields, models
from odoo.tools import frozendict, is_html_empty

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
    reversed_entry_id = fields.Many2one(tracking=True)
    l10n_ae_company_country_code = fields.Char(string="Company Country Code", related='company_id.country_code')
    l10n_ae_beneficiary_id = fields.Char(string='Beneficiary ID')
    l10n_ae_principal_id = fields.Char(string='Principal ID')
    l10n_ae_uuid = fields.Char(
        string='AE PINT UUID',
        default=lambda self: str(uuid.uuid4()),
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
        """ A draft follows its fiscal position: an export under one that isn't for the UAE, not
        otherwise. The other types are left as they are.
        """
        exports = self.env.ref('l10n_ae_ubl_pint.transaction_type_exports', raise_if_not_found=False)
        for move in self:
            transaction_types = move.l10n_ae_transaction_type_ids
            if (
                exports
                and move.country_code == 'AE'
                and move.state == 'draft'
                and move.move_type in ('out_invoice', 'out_refund')
            ):
                if move._l10n_ae_is_foreign_fiscal_position():
                    transaction_types |= exports
                else:
                    transaction_types -= exports
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

    def _l10n_ae_get_predefined_buyer_endpoint(self):
        """ The predefined endpoint (scheme 0235) the buyer of a customer invoice or credit note gets
        instead of its own, None to keep its own (MoF e-invoicing guidelines, 10.2.2, 10.4, 18.3.3):

        - Deemed Supply: 9900000097, whoever the buyer.
        - A buyer on Peppol keeps its own endpoint.
        - A buyer not on Peppol (not yet on e-invoicing), Exports not selected: 9900000098.
        - Exports to a non-UAE buyer on Peppol keeps its own endpoint.
        - Exports to a non-UAE buyer not on Peppol: 9900000099.

        Not on Peppol: not verified as such, the Peppol status being verified when sending.

        https://mof.gov.ae/wp-content/uploads/2026/10/UAE-Electronic-Invoicing-Guidelines_En.pdf
        """
        self.ensure_one()
        if not self.is_sale_document():
            return None
        if self._l10n_ae_has_transaction_type('01000000'):
            return '9900000097'
        buyer = self.commercial_partner_id.with_company(self.company_id)
        if buyer.peppol_verification_state == 'valid':
            return None
        if self._l10n_ae_has_transaction_type('00000001'):
            return '9900000099'
        return '9900000098'

    @api.depends('partner_id', 'country_code', 'journal_id.is_self_billing')
    def _compute_l10n_ae_invoice_type(self):
        """ A tax invoice for a company, a simplified one for an individual, on drafts only. A posted invoice keeps
        its type, it only gets one when it has none (posted before this module was installed).

        A self-billed document has none: it is always a tax invoice (389/261), there is no self-billing of
        commercial invoices (MoF e-invoicing guidelines, 10.3).
        https://mof.gov.ae/wp-content/uploads/2026/10/UAE-Electronic-Invoicing-Guidelines_En.pdf
        """
        for move in self:
            if move.is_purchase_document() and move.journal_id.is_self_billing:
                move.l10n_ae_invoice_type = False
            elif move.state != 'draft' and move.l10n_ae_invoice_type:
                continue
            elif move.country_code != 'AE':
                move.l10n_ae_invoice_type = False
            else:
                move.l10n_ae_invoice_type = 'tax' if move.partner_id.commercial_partner_id.is_company else 'simplified'

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

    def _l10n_ae_pint_get_errors(self):
        """ The PINT AE rules on the invoice's own data.

        - ibr-007-ae: Beneficiary ID (BTAE-01) for a Free Trade Zone supply.
        - ibr-137-ae: Principal ID (BTAE-14) for a Disclosed Agent Billing.
        - ibr-160-ae: an "Others" billing frequency is described in the note (IBT-022), built
          from the Terms & Conditions.
        - ibr-158-ae: Credit note reason code (BTAE-03) on a credit note, commercial ones included
          since ibr-055-ae compares the reference against it.
        - ibr-055-ae: a credit note references the invoice it credits, unless its reason is
          Volume Discount (the export then drops the reference).
        """
        self.ensure_one()
        errors = []
        if self._l10n_ae_has_transaction_type('10000000') and not self.l10n_ae_beneficiary_id:
            errors.append(frozendict({
                'message': self.env._("Invoice(s) for a Free Trade Zone supply should have their Beneficiary ID set."),
                'error_code': 'l10n_ae_pint_move_beneficiary_id_missing',
                'level': 'danger',
            }))
        if self._l10n_ae_has_transaction_type('00000100') and not self.l10n_ae_principal_id:
            errors.append(frozendict({
                'message': self.env._("Invoice(s) for a Disclosed Agent Billing supply should have their Principal ID set."),
                'error_code': 'l10n_ae_pint_move_principal_id_missing',
                'level': 'danger',
            }))
        # self.invoice_payment_term_id.l10n_ae_billing_frequency == 'OTH' use the name of the record rather than blocking ALKH
        if self.invoice_payment_term_id.l10n_ae_billing_frequency == 'OTH' and is_html_empty(self.narration):
            errors.append(frozendict({
                'message': self.env._(
                    "Invoice(s) with an \"Others\" billing frequency should describe it in their Terms & Conditions.",
                ),
                'error_code': 'l10n_ae_pint_move_billing_frequency_note_missing',
                'level': 'danger',
            }))
        if self._l10n_ae_is_credit_note():
            if not self.l10n_ae_credit_note_reason:
                errors.append(frozendict({
                    'message': self.env._("Credit note(s) should have their Credit Note Reason set."),
                    'error_code': 'l10n_ae_pint_move_credit_note_reason_missing',
                    'level': 'danger',
                }))
            if self.l10n_ae_credit_note_reason != 'VD' and not self._l10n_ae_get_preceding_invoices():
                errors.append(frozendict({
                    'message': self.env._(
                        "Credit note(s) should be linked to an invoice. Set the invoice in \"Reversal Of\" (Other Info tab > FTA)",
                    ),
                    'error_code': 'l10n_ae_pint_move_preceding_invoice_missing',
                    'level': 'danger',
                }))
        return errors

    def _l10n_ae_is_credit_note(self):
        """ Whether this move is exported as a PINT AE credit note, self-billed ones included. """
        self.ensure_one()
        return self.move_type == 'out_refund' or (self.move_type == 'in_refund' and self.journal_id.is_self_billing)

    def _l10n_ae_get_preceding_invoices(self):
        """ The preceding invoices (IBG-03) the export references: the reconciled ones, else the reversed one. """
        self.ensure_one()
        invoice_type = 'out_invoice' if self.move_type == 'out_refund' else 'in_invoice'

        def named_invoices(moves):
            return moves.filtered(lambda move: move.move_type == invoice_type and move.name and move.name != '/')

        return named_invoices(self._get_reconciled_invoices()) or named_invoices(self.reversed_entry_id)

    def l10n_ae_get_payment_means_details(self):
        """ The UNCL4461 payment means code and name, from the preferred payment method's journal. """
        self.ensure_one()
        payment_method_line = self.preferred_payment_method_line_id
        if payment_method_line.journal_id.type == 'cash':
            return 10, 'In cash'
        if payment_method_line.journal_id.type == 'bank' or self.partner_bank_id:
            return 30, 'Credit transfer'
        return 1, 'Instrument not defined'
