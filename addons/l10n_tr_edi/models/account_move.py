import uuid

from odoo import _, Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL, float_compare

from odoo.addons.l10n_tr_edi.const import (
    EXEMPTION_CODE_TYPES,
    GIB_INVOICE_SCENARIO_SELECTION,
    GIB_INVOICE_TYPE_SELECTION,
)


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move']

    l10n_tr_nilvera_uuid = fields.Char(
        string="Nilvera Document UUID",
        copy=False,
        readonly=True,
        help="This is the unique identifier (UUID) used to link this Odoo document with the Nilvera system. \n"
        "This record ensures every new document has its own unique ID for tracking.",
    )
    l10n_tr_nilvera_send_status = fields.Selection(
        selection=[
            ('cancelled', 'Cancelled'),
            ('error', "Error"),
            ('not_sent', "Not sent"),
            ('sent', "Sent and waiting response"),
            ('succeed', "Successful"),
            ('waiting', "Waiting"),
            ('unknown', "Unknown"),
            ('commercial_approved', "Approved"),
            ('commercial_answered_automatically', "Approved Automatically"),
            ('commercial_rejected', "Rejected"),
            ('draft_sent', "Sent as Draft"),
        ],
        string="Nilvera Status",
        readonly=True,
        copy=False,
        default='not_sent',
        help="Tracks the real-time submission status of this invoice to Nilvera. It is updated automatically based on "
             "responses from Nilvera and GİB. \n"
             "This field is read-only as it is updated automatically by the system based on responses from Nilvera and GİB. \n"
             "- Not sent: Default state before processing. \n"
             "- Sent and waiting response: Sent to Nilvera, awaiting GİB confirmation. \n"
             "- Successful: GİB has accepted the invoice. \n"
             "- Error: The submission failed (check chatter for details). \n"
             "- Approved: Commercial Invoice is approved by recipient.\n"
             "- Approved Automatically: Commercial Invoice is automatically approved after 8 days without a response.\n"
             "- Rejected: Commercial Invoice is rejected by recipient.\n"
             "- Sent as Draft: Uploaded to Nilvera as a draft."
             "It is approved and transmitted to GİB when the invoice is sent.",
    )
    l10n_tr_gib_invoice_scenario = fields.Selection(
        selection=GIB_INVOICE_SCENARIO_SELECTION,
        default='TEMELFATURA',
        string="Invoice Scenario",
        help="Defines the official GİB (Turkish Revenue Administration) e-invoice "
        "scenario. \n"
        "- Basic: Standard e-invoice that cannot be rejected by the recipient via the GİB portal. \n"
        "- Public Sector: Used specifically for invoices issued to public (government) institutions.\n"
        "- Commercial: Allows the recipient to accept or reject the invoice via GİB.",
    )
    l10n_tr_gib_invoice_type = fields.Selection(
        compute='_compute_l10n_tr_gib_invoice_type',
        store=True,
        readonly=False,
        recursive=True,
        string="GIB Invoice Type",
        selection=GIB_INVOICE_TYPE_SELECTION,
        help="Specifies the official GİB classification for the e-invoice/e-archive, which "
        "determines its tax treatment and validation rules. \n"
        "- Sales: A standard sales invoice. \n"
        "Withholding: An invoice where the buyer is responsible for "
        "- paying a portion of the VAT. \n"
        "Registered for Export: Invoice for goods that will later be exported."
        "- If selected, an 'Exemption Reason' is required. \n"
        "- Tax Exempt: An invoice for goods/services exempt from VAT. "
        "If selected, an 'Exemption Reason' is required.\n"
        "- Return: Reverses a previously issued sales invoice for returned or canceled goods/services.\n"
        "- Withholding Return: Reverses a previously issued withholding invoice.\n",
    )
    l10n_tr_is_export_invoice = fields.Boolean(
        string="GİB Product Export Invoice",
        help="Check this box if this is a product export invoice.",
    )
    l10n_tr_sales_type = fields.Selection(
        selection=[
            ('normal', "Normal Sale"),
            ('website', "Website Sale"),
        ],
        compute='_compute_l10n_tr_sales_type',
        string="Sales Type",
        store=True,
        readonly=False,
        copy=False,
    )
    l10n_tr_shipping_type = fields.Selection(
        selection=[
            ('1', "Sea Transportation"),
            ('2', "Railway Transportation"),
            ('3', "Road Transportation"),
            ('4', "Air Transportation"),
            ('5', "Post"),
            ('6', "Combined Transportation"),
            ('7', "Fixed Transportation"),
            ('8', "Domestic Water Transportation"),
            ('9', "Invalid Transportation Method"),
        ],
        string="Shipping Method",
        help="Specifies the method of transport using official GİB codes. ",
    )
    l10n_tr_exemption_code_id = fields.Many2one(
        comodel_name='l10n_tr_nilvera_einvoice.account.tax.code',
        compute='_compute_l10n_tr_exemption_code_id',
        store=True,
        readonly=False,
        string="Exemption Reason",
        help="The official GİB tax exemption reason, or, for a withholding invoice, the "
        "official GİB withholding reason. \n"
        "This field is mandatory if the 'GIB Invoice Type' is set to "
        "'Registered for Export', 'Tax Exempt' or 'Withholding'.",
    )
    l10n_tr_available_exemption_code_ids = fields.Many2many(
        comodel_name='l10n_tr_nilvera_einvoice.account.tax.code',
        compute='_compute_l10n_tr_available_exemption_code_ids',
        compute_sudo=True,
        help="Technical field (not for users). The GİB codes available on this invoice, from "
        "the selected GIB Invoice Type and, for a withholding invoice, from the ratio its "
        "lines withhold.",
    )
    l10n_tr_withholding_ratio = fields.Float(
        compute='_compute_l10n_tr_withholding_ratio',
        help="Technical field (not for users). The VAT fraction the invoice lines withhold, "
        "0.9 for a 9/10 withholding, 0 when they withhold nothing or withhold at "
        "several ratios.",
    )
    l10n_tr_zero_vat_warning = fields.Boolean(compute="_compute_l10n_tr_l10n_tr_zero_vat_warning")
    l10n_tr_nilvera_customer_status = fields.Selection(
        string="Partner Nilvera Status",
        related='partner_id.l10n_tr_nilvera_customer_status',
        help="Shows the Nilvera status of the customer. ",
    )
    l10n_tr_original_invoice_date = fields.Date(string="Original Invoice Date")
    l10n_tr_public_spending_unit_id = fields.Many2one(comodel_name='res.partner',
        string='Public Spending Unit',
        store=True,
        readonly=False,
        compute='_compute_l10n_tr_public_spending_unit_id',
    )
    l10n_tr_invoice_scenario_group = fields.Selection(
        selection=[
            ('basic', "Basic Scenario"),
            ('public', "Public Scenario"),
            ('commercial', "Commercial Scenario"),
            ('earchive', "e-Archive"),
            ('export', "Export Invoice"),
        ],
        string="Invoice Scenario Group",
        compute='_compute_l10n_tr_invoice_scenario_group',
        compute_sql='_compute_sql_invoice_scenario_group',
        compute_sudo=True,
    )

    @api.depends('l10n_tr_is_export_invoice', 'partner_id.l10n_tr_nilvera_customer_status', 'l10n_tr_gib_invoice_scenario')
    def _compute_l10n_tr_invoice_scenario_group(self):
        for record in self:
            if record.l10n_tr_is_export_invoice:
                record.l10n_tr_invoice_scenario_group = 'export'
            elif record.l10n_tr_nilvera_customer_status == 'earchive':
                record.l10n_tr_invoice_scenario_group = 'earchive'
            elif record.l10n_tr_gib_invoice_scenario == 'TEMELFATURA':
                record.l10n_tr_invoice_scenario_group = 'basic'
            elif record.l10n_tr_gib_invoice_scenario == 'KAMU':
                record.l10n_tr_invoice_scenario_group = 'public'
            elif record.l10n_tr_gib_invoice_scenario == 'TICARIFATURA':
                record.l10n_tr_invoice_scenario_group = 'commercial'
            else:
                record.l10n_tr_invoice_scenario_group = False

    def _compute_sql_invoice_scenario_group(self, table):
        partner_table = table._join('partner_id')
        return SQL(
            """
            CASE
                WHEN %(export)s = TRUE               THEN 'export'
                WHEN %(partner_status)s = 'earchive' THEN 'earchive'
                WHEN %(scenario)s = 'TEMELFATURA'    THEN 'basic'
                WHEN %(scenario)s = 'KAMU'           THEN 'public'
                WHEN %(scenario)s = 'TICARIFATURA'   THEN 'commercial'
                ELSE NULL
            END
            """,
            export=table['l10n_tr_is_export_invoice'],
            partner_status=partner_table['l10n_tr_nilvera_customer_status'],
            scenario=table['l10n_tr_gib_invoice_scenario'],
        )

    @api.depends('move_type', 'l10n_tr_gib_invoice_scenario')
    def _compute_l10n_tr_public_spending_unit_id(self):
        for record in self:
            if record.move_type == 'out_invoice' and record.l10n_tr_gib_invoice_scenario == 'KAMU':  # Public Scenario Invoices
                record.l10n_tr_public_spending_unit_id = record.l10n_tr_public_spending_unit_id or record.partner_id
            else:
                record.l10n_tr_public_spending_unit_id = False

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_l10n_tr_l10n_tr_zero_vat_warning(self):
        exempt_zero_tax = self.env['account.chart.template'].ref('tr_s_0_ex', raise_if_not_found=False)
        for invoice in self:
            invoice.l10n_tr_zero_vat_warning = exempt_zero_tax and invoice.l10n_tr_gib_invoice_type == 'SATIS' and exempt_zero_tax in invoice.line_ids.tax_ids

    @api.depends('invoice_line_ids.tax_ids.children_tax_ids.amount')
    def _compute_l10n_tr_withholding_ratio(self):
        for record in self:
            # Only what we issue: an incoming document keeps the type its supplier sent.
            if not record.is_sale_document(include_receipts=True):
                record.l10n_tr_withholding_ratio = 0.0
                continue
            record.l10n_tr_withholding_ratio = record.invoice_line_ids.tax_ids._l10n_tr_get_withholding_ratio()

    @api.depends(
        "l10n_tr_gib_invoice_type",
        "l10n_tr_is_export_invoice",
        "l10n_tr_withholding_ratio",
    )
    def _compute_l10n_tr_available_exemption_code_ids(self):
        codes = self.env['l10n_tr_nilvera_einvoice.account.tax.code'].search([])
        for record in self:
            if record.l10n_tr_is_export_invoice:
                code_types = {'export_exception'}
            else:
                code_types = EXEMPTION_CODE_TYPES.get(record.l10n_tr_gib_invoice_type, set())
            record_codes = codes.filtered(lambda code: code.code_type in code_types)
            if 'withholding' in code_types:
                # Only keep the reasons matching the rate the lines actually withhold.
                ratio = record.l10n_tr_withholding_ratio
                record_codes = record_codes.filtered(
                    lambda code: float_compare(code.percentage, ratio, precision_digits=4) == 0,
                )
            record.l10n_tr_available_exemption_code_ids = record_codes

    @api.depends(
        "l10n_tr_gib_invoice_scenario",
        "l10n_tr_is_export_invoice",
        "move_type",
        "reversed_entry_id.l10n_tr_gib_invoice_type",
        "l10n_tr_withholding_ratio",
    )
    def _compute_l10n_tr_gib_invoice_type(self):
        for record in self:
            # Off the lines, not the position: it only applies on `Update Taxes and Accounts`.
            withholds = record.l10n_tr_withholding_ratio
            if record.l10n_tr_is_export_invoice:
                record.l10n_tr_gib_invoice_type = 'ISTISNA'
            elif record.move_type == 'out_refund':
                # A return mirrors the invoice it reverses, which is what `_reverse_moves` writes.
                origin_withholds = record.reversed_entry_id.l10n_tr_gib_invoice_type == 'TEVKIFAT'
                record.l10n_tr_gib_invoice_type = 'TEVKIFATIADE' if origin_withholds or withholds else 'IADE'
            elif withholds:
                record.l10n_tr_gib_invoice_type = 'TEVKIFAT'
            else:
                record.l10n_tr_gib_invoice_type = 'SATIS'

    @api.depends(
        "l10n_tr_gib_invoice_scenario",
        "l10n_tr_gib_invoice_type",
        "partner_id",
        "l10n_tr_available_exemption_code_ids",
    )
    def _compute_l10n_tr_exemption_code_id(self):
        for record in self:
            code = record.l10n_tr_exemption_code_id
            if not record._l10n_tr_reason_is_consistent():
                available_codes = record.l10n_tr_available_exemption_code_ids
                # only one reason fits the ratio, e.g. 3/10, so there is nothing to choose
                code = available_codes if len(available_codes) == 1 else False
            record.l10n_tr_exemption_code_id = code

    def _l10n_tr_reason_is_consistent(self):
        """Whether the reason on this invoice still fits its type and its line taxes.

        Checked against the reason itself, not against the available ids, so a reason
        created on the spot for a ratio no shipped GİB code covers survives a recompute.
        """
        self.ensure_one()
        code = self.l10n_tr_exemption_code_id
        if not code:
            return False
        if self.l10n_tr_is_export_invoice:
            return code.code_type == 'export_exception'
        if code.code_type not in EXEMPTION_CODE_TYPES.get(self.l10n_tr_gib_invoice_type, set()):
            return False
        if code.code_type != 'withholding':
            return True
        return float_compare(code.percentage, self.l10n_tr_withholding_ratio, precision_digits=4) == 0

    @api.depends('partner_id')
    def _compute_l10n_tr_sales_type(self):
        for move in self:
            if (
                move.country_code == 'TR'
                and move.is_sale_document()
                and move.l10n_tr_nilvera_customer_status == 'earchive'
            ):
                move.l10n_tr_sales_type = 'website' if 'website_id' in move._fields and move.website_id else 'normal'
            else:
                move.l10n_tr_sales_type = None

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        # Fill scenario and type based on the latest invoice.
        if self.partner_id and (invoice := self.env['account.move'].search([
            ('id', 'not in', self.ids),
            ('move_type', '=', self.move_type),
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
        ], limit=1)):
            self.l10n_tr_gib_invoice_scenario = invoice.l10n_tr_gib_invoice_scenario
            self.l10n_tr_gib_invoice_type = invoice.l10n_tr_gib_invoice_type if not self.l10n_tr_is_export_invoice else 'ISTISNA'

        super()._onchange_partner_id()

    def _get_import_file_type(self, file_data):
        """ Identify Nilvera UBL files. """
        # EXTENDS 'account'
        if (
            file_data['xml_tree'] is not None
            and (customization_id := file_data['xml_tree'].findtext('{*}CustomizationID'))
            and 'TR1.2' in customization_id
        ):
            return 'account.edi.xml.ubl.tr'

        return super()._get_import_file_type(file_data)

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'TR1.2' in customization_id.text:
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def button_draft(self):
        # EXTENDS account
        for move in self.filtered(lambda move: move.l10n_tr_nilvera_uuid and move.move_type in {'out_invoice', 'in_invoice'}):
            if move.l10n_tr_nilvera_send_status == 'error':
                move.message_post(body=_("To preserve accounting integrity and comply with legal requirements, invoices cannot be reused once an error occurs. Please create a new invoice to continue."))
            elif move.l10n_tr_nilvera_send_status not in {'not_sent', 'draft_sent', 'commercial_rejected'}:
                raise UserError(_("You cannot reset to draft an entry that has been sent/received from Nilvera."))
        return super().button_draft()

    def _l10n_tr_nilvera_einvoice_check_invalid_invoice_reference(self):
        invalid_moves = self.env["account.move"]
        for record in self:
            _, parts = record._get_sequence_format_param(record.ref or "")
            if (
                record.move_type == "out_refund"
                and not record.reversed_entry_id
                and not (parts["prefix1"][:3] and parts["year"] and parts["seq"])
            ):
                invalid_moves |= record
        return invalid_moves

    def _l10n_tr_get_partner_control_account(self):
        self.ensure_one()
        partner = self.partner_id.with_company(self.company_id)
        if self.move_type in self.get_purchase_types():
            return partner.property_account_payable_id
        return partner.property_account_receivable_id

    def _l10n_tr_get_einvoice_sequence(self):
        """Get the e-Document sequence of the journal that applies to this document.

        :return: the series to number this document with, empty if it falls back to the journal.
        """
        self.ensure_one()
        if self.move_type not in self.get_invoice_types() or self.country_code != 'TR':
            return None
        candidates = self.journal_id.sudo().l10n_tr_einvoice_sequence_ids.filtered(
            lambda s: s._l10n_tr_matches_move(self),
        )
        return candidates.sorted(lambda s: s._l10n_tr_specificity_key(), reverse=True)[:1]

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS account
        condition = super()._get_last_sequence_domain(relaxed)
        if not self.journal_id or self.country_code != 'TR':
            return condition
        if series := self._l10n_tr_get_einvoice_sequence():
            return SQL(
                "%(condition)s AND sequence_prefix LIKE %(series_prefix)s",
                condition=condition,
                series_prefix=f"{series.name}/%",
            )
        # No series applies, so this document falls back to the journal's own numbering.
        return SQL(
            """
            %(condition)s
            AND sequence_prefix NOT LIKE ALL (COALESCE((
                SELECT array_agg(l10n_tr_series.name || '/%%')
                  FROM l10n_tr_nilvera_einvoice_invoice_sequence l10n_tr_series
                 WHERE l10n_tr_series.journal_id = %(journal_id)s
            ), ARRAY[]::text[]))
            """,
            condition=condition,
            journal_id=self.journal_id.id,
        )

    def _post(self, soft=True):
        for move in self:
            if move.l10n_tr_nilvera_send_status == 'error' and move.l10n_tr_nilvera_uuid:
                raise UserError(_("To preserve accounting integrity and comply with legal requirements, invoices cannot be reused once an error occurs. Please create a new invoice to continue."))
            if move.country_code == 'TR' and not move.l10n_tr_nilvera_uuid:
                move.l10n_tr_nilvera_uuid = str(uuid.uuid4())
        return super()._post(soft=soft)

    def _l10n_tr_nilvera_get_series_prefix(self):
        """Return the 3-character invoice series for an unnamed draft.

        A draft has no sequence number yet. The series is derived from the last sequence
        used on this journal/period, falling back to the journal code; if neither yields
        a usable value, it is left empty.
        """
        self.ensure_one()
        last_sequence = self._get_last_sequence() or self._get_last_sequence(relaxed=True)
        if last_sequence:
            _, parts = self._get_sequence_format_param(last_sequence)
            prefix = parts['prefix1'][:3]
        else:
            prefix = self.journal_id.code or ''
        return prefix

    def _l10n_tr_nilvera_einvoice_check_negative_lines(self):
        return any(
            line.display_type not in {'line_note', 'line_section'}
            and (line.quantity < 0 or line.price_unit < 0)
            for line in self.invoice_line_ids
        )

    def _l10n_tr_nilvera_einvoice_check_lines_missing_taxes(self):
        return any(
            line.display_type == 'product' and not line.tax_ids
            for line in self.invoice_line_ids
        )

    def _get_starting_sequence(self):
        """
        Generate a valid name for credit notes.

        Nilvera requires invoice names in the format:
        <3 alphanumeric characters>/<year>/<sequence number>.

        When creating a credit note, an R is added by standard, so
        we remove the first letter of the journal prefix to make sure it
        remains 3 characters (e.g., RINV → RNV).

        When an e-Document sequence of the journal applies, its series code takes the place
        of the journal code instead. The series code is already 3 characters, and credit notes
        get their own series through the "Credit Note" condition, so no R is added to it.
        """
        starting_sequence = super()._get_starting_sequence()
        if series := self._l10n_tr_get_einvoice_sequence():
            _old_name, separator, rest = starting_sequence.partition('/')
            if separator:
                return f"{series.name}{separator}{rest}"
        if (
            self.company_id.country_id.code == "TR"
            and self.journal_id.refund_sequence
            and self.move_type in {"out_refund", "in_refund"}
        ):
            starting_sequence = starting_sequence[0] + starting_sequence[2:]
        return starting_sequence

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if all(move.country_code != 'TR' or move.move_type != "out_invoice" for move in self):
            return super()._reverse_moves(default_values_list, cancel=cancel)

        if not default_values_list:
            default_values_list = [{}] * len(self)

        for default_vals, move in zip(default_values_list, self):
            if move.country_code != 'TR' or move.move_type != "out_invoice":
                continue
            line_vals = move.line_ids.with_context(move_reverse_cancel=cancel).copy_data()
            for line, vals in zip(move.line_ids, line_vals):
                vals.update(
                    {
                        "l10n_tr_original_line_id": line.id,
                        "l10n_tr_original_quantity": line.quantity,
                        "l10n_tr_original_tax_without_withholding": line.price_total - line.price_subtotal,
                    },
                )
            default_vals.update(
                {
                    'ref': move.name,
                    'l10n_tr_gib_invoice_scenario': 'TEMELFATURA',
                    'l10n_tr_gib_invoice_type': 'TEVKIFATIADE' if move.l10n_tr_gib_invoice_type == "TEVKIFAT" else "IADE",
                    'line_ids': [Command.create(vals) for vals in line_vals],
                },
            )

        return super()._reverse_moves(default_values_list, cancel=cancel)
