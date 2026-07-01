
import uuid

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ae_invoice_transaction_type = fields.Selection(
        string='Invoice Transaction Type',
        compute="_compute_transaction_code",
        selection=[
            ('00000000', 'No Transaction Type'),
            ('10000000', 'Free Trade Zone'),
            ('01000000', 'Deemed Supply'),
            ('00100000', 'Profit Margin Scheme'),
            ('00010000', 'Summary Invoice'),
            ('00001000', 'Continuous Supply'),
            ('00000100', 'Disclosed Agent Billing'),
            ('00000010', 'Supply through e-commerce'),
            ('00000001', 'Exports'),
        ],
        default='00000000',
        readonly=False,
        store=True,
    )
    l10n_ae_is_out_of_scope = fields.Boolean(
        string="Out of Scope",
        compute="_compute_out_of_scope",
        store=True,
    )
    l10n_ae_is_volume_discount = fields.Boolean(
        string='Volume Discount Credit Note',
    )

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_transaction_code(self):
        # AE-specific: InvoiceTypeCode must be explicitly set (default = "00000000")-> No Special Transcation Type.
        # It is an 8-character binary string where each position represents a transaction type. An invoice can be
        # of different transcation types. Thus, we use "1" if applicable, "0" if not.
        #
        # Format (left → right):
        # 1. Free Trade Zone           → 10000000
        # 2. Deemed Supply             → 01000000
        # 3. Profit Margin Scheme      → 00100000
        # 4. Summary Invoice           → 00010000
        # 5. Continuous Supply         → 00001000
        # 6. Disclosed Agent Billing   → 00000100
        # 7. E-commerce Supply         → 00000010
        # 8. Exports                   → 00000001
        # Reference:
        # see https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/bis/#_invoice_transaction_type_code
        for move in self:
            # Collect all taxes used in invoice lines
            fiscal_position_ids = move.invoice_line_ids.tax_ids.fiscal_position_ids.mapped('tax_ids')
            fiscal_position_xml_ids = fiscal_position_ids.get_external_id().values()
            # Export
            if any('account_fiscal_position_non_uae_countries' in (xml or '') for xml in fiscal_position_xml_ids):
                move.l10n_ae_invoice_transaction_type = '00000001'

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_out_of_scope(self):
        for move in self:
            taxes = move.invoice_line_ids.mapped('tax_ids')
            tax_xml_ids = taxes.get_external_id().values()

            move.l10n_ae_is_out_of_scope = any(
                'uae_out_of_scope' in (xml or '')
                for xml in tax_xml_ids
            )

    def _l10n_ae_get_uuid(self):
        """ AE Pint requires us to generate a uuid, to avoid storing a new field on the move,
        we derive it from the dbuuid and the move id. """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        guid = uuid.uuid5(namespace=uuid.UUID(dbuuid), name=str(self.id))
        return str(guid)

    def l10n_ae_get_payment_means_details(self):
        if self.partner_bank_id:
            return 30, 'Credit transfer'
        return 1, 'Instrument not defined'
