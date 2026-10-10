import re
import uuid
from collections import defaultdict

from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL, float_compare

from odoo.addons.l10n_tr_edi.const import (
    COMMERCIAL_ANSWER_TO_DOCUMENT_STATE,
    COMMERCIAL_RESPONSE_STATE_TO_SEND_STATUS,
    DOCUMENT_STATE_TO_SEND_STATUS,
    EXEMPTION_CODE_TYPES,
    GIB_INVOICE_SCENARIO_SELECTION,
    GIB_INVOICE_TYPE_SELECTION,
    GIB_RETURN_INVOICE_TYPES,
)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_tr_edi_uuid = fields.Char(
        string="E-Document UUID",
        copy=False,
        readonly=True,
        help="This is the unique identifier (UUID) used to link this Odoo document with the GİB system. \n"
        "This record ensures every new document has its own unique ID for tracking.",
    )
    l10n_tr_edi_customer_status = fields.Selection(
        string="Partner GİB Status",
        related='partner_id.l10n_tr_edi_customer_status',
        help="Shows the GİB status of the customer. ",
    )
    l10n_tr_edi_document_ids = fields.One2many(
        comodel_name='l10n_tr_edi.document',
        inverse_name='move_id',
        copy=False,
        readonly=True,
    )
    l10n_tr_edi_can_cancel = fields.Boolean(compute='_compute_l10n_tr_edi_can_cancel')
    l10n_tr_edi_send_status = fields.Selection(
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
        string="E-Document Status",
        compute='_compute_l10n_tr_edi_send_status',
        store=True,
        copy=False,
        init_storage=lambda model: model.env.cr.execute(
            "UPDATE account_move SET l10n_tr_edi_send_status = 'not_sent' WHERE l10n_tr_edi_send_status IS NULL",
        ),
        help="Tracks the real-time submission status of this invoice to the GİB. It is updated automatically based on "
             "responses from the provider and the GİB. \n"
             "This field is read-only as it is updated automatically by the system based on responses from the provider and the GİB. \n"
             "- Not sent: Default state before processing. \n"
             "- Sent and waiting response: Sent to the provider, awaiting GİB confirmation. \n"
             "- Waiting: GİB is processing the invoice. \n"
             "- Successful: GİB has accepted the invoice. \n"
             "- Error: GİB rejected the invoice (see the e-Documents tab); it cannot be reused. \n"
             "- Cancelled: The e-Archive invoice has been cancelled. \n"
             "- Approved: Commercial Invoice is approved by recipient.\n"
             "- Approved Automatically: Commercial Invoice is automatically approved after 8 days without a response.\n"
             "- Rejected: Commercial Invoice is rejected by recipient.\n"
             "- Sent as Draft: Uploaded to the provider as a draft. "
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
        comodel_name='l10n_tr_edi.tax.code',
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
        comodel_name='l10n_tr_edi.tax.code',
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
        compute_sql='_compute_sql_l10n_tr_invoice_scenario_group',
        compute_sudo=True,
    )

    @api.depends('l10n_tr_edi_document_ids.state', 'l10n_tr_edi_document_ids.document_type')
    def _compute_l10n_tr_edi_send_status(self):
        for move in self:
            documents = move.l10n_tr_edi_document_ids.sorted()
            response = documents.filtered(lambda d: d.document_type == 'commercial_response')[:1]
            document = (documents - response)[:1]
            if response.state in COMMERCIAL_RESPONSE_STATE_TO_SEND_STATUS:
                move.l10n_tr_edi_send_status = COMMERCIAL_RESPONSE_STATE_TO_SEND_STATUS[response.state]
            elif document:
                move.l10n_tr_edi_send_status = DOCUMENT_STATE_TO_SEND_STATUS.get(document.state, 'not_sent')
            else:
                move.l10n_tr_edi_send_status = 'not_sent'

    @api.depends('l10n_tr_is_export_invoice', 'partner_id.l10n_tr_edi_customer_status', 'l10n_tr_gib_invoice_scenario')
    def _compute_l10n_tr_invoice_scenario_group(self):
        for record in self:
            if record.l10n_tr_is_export_invoice:
                record.l10n_tr_invoice_scenario_group = 'export'
            elif record.partner_id.l10n_tr_edi_customer_status == 'earchive':
                record.l10n_tr_invoice_scenario_group = 'earchive'
            elif record.l10n_tr_gib_invoice_scenario == 'TEMELFATURA':
                record.l10n_tr_invoice_scenario_group = 'basic'
            elif record.l10n_tr_gib_invoice_scenario == 'KAMU':
                record.l10n_tr_invoice_scenario_group = 'public'
            elif record.l10n_tr_gib_invoice_scenario == 'TICARIFATURA':
                record.l10n_tr_invoice_scenario_group = 'commercial'
            else:
                record.l10n_tr_invoice_scenario_group = False

    def _compute_sql_l10n_tr_invoice_scenario_group(self, table):
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
            partner_status=partner_table['l10n_tr_edi_customer_status'],
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
        codes = self.env['l10n_tr_edi.tax.code'].search([])
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
                and move.partner_id.l10n_tr_edi_customer_status == 'earchive'
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
        """ Identify UBL-TR files. """
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
        # EXTENDS 'account'
        for move in self.filtered(lambda move: move.l10n_tr_edi_uuid and move.move_type in {'out_invoice', 'in_invoice'}):
            if move.l10n_tr_edi_send_status == 'error':
                move.message_post(body=self.env._("To preserve accounting integrity and comply with legal requirements, invoices cannot be reused once an error occurs. Please create a new invoice to continue."))
            elif move.l10n_tr_edi_send_status not in {'not_sent', 'draft_sent', 'commercial_rejected'}:
                raise UserError(self.env._("You cannot reset to draft an entry that has been sent to or received from the GİB."))
        return super().button_draft()

    def _post(self, soft=True):
        for move in self:
            if move.l10n_tr_edi_send_status == 'error' and move.l10n_tr_edi_uuid:
                raise UserError(self.env._("To preserve accounting integrity and comply with legal requirements, invoices cannot be reused once an error occurs. Please create a new invoice to continue."))
            if move.country_code == 'TR' and not move.l10n_tr_edi_uuid:
                move.l10n_tr_edi_uuid = str(uuid.uuid4())
        return super()._post(soft=soft)

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

    def _l10n_tr_edi_get_series_prefix(self):
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

    def _l10n_tr_edi_check_negative_lines(self):
        return any(
            line.display_type not in {'line_note', 'line_section'}
            and (line.quantity < 0 or line.price_unit < 0)
            for line in self.invoice_line_ids
        )

    def _l10n_tr_edi_check_lines_missing_taxes(self):
        return any(
            line.display_type == 'product' and not line.tax_ids
            for line in self.invoice_line_ids
        )

    def _l10n_tr_edi_check_invalid_invoice_reference(self):
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

    def _l10n_tr_edi_get_alerts(self):
        """Return the GİB checks failing on the invoices about to be sent as Turkish e-Documents."""
        def _is_valid_gib_name(move):
            _, parts = move._get_sequence_format_param(move.name)

            return (
                parts['year'] != 0
                and parts['year_length'] == 4
                and parts['seq'] != 0
                and re.match(r'^[A-Za-z0-9]{3}[^A-Za-z0-9]?$', parts['prefix1'])
            )

        alerts = {}

        if tr_companies_missing_required_codes := self.company_id.filtered(
            lambda c: c.country_code == 'TR'
            and not c.partner_id._get_additional_identifier('TR_MERSIS')
            and not c.partner_id._get_additional_identifier('TR_TICARET_SICIL')
        ):
            alerts["tr_companies_missing_required_codes"] = {
                "message": _("Please ensure that your company contact has either the 'Mersis Number' or 'Trade Registry Number' has a value."),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_required_codes.partner_id._get_records_action(name=_("Check company(s)")),
                "level": "danger",
            }

        # Alert if company is missing required data (country = TR, and tax ID, city, state, street)
        if tr_companies_missing_required_fields := self.filtered(
            lambda m: (
                not m.company_id.vat
                or not m.company_id.street
                or not m.company_id.city
                or not m.company_id.state_id
                or m.company_id.country_code != 'TR'
            )
        ).company_id:
            alerts["tr_companies_missing_required_fields"] = {
                'level': 'danger',
                "message": _(
                    "The following company(s) either do not have their country set as Türkiye "
                    "or are missing at least one of these fields: Tax ID, Street, City, or State"
                ),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_required_fields._get_records_action(name=_(
                    "Check Tax ID, City, Street, State, and Country or Company(s)"
                )),
            }

        # Alert if partner is missing required data (tax ID, street, city, state, country)
        if tr_partners_missing_required_fields := self._l10n_tr_edi_get_partner_address_alert():
            alerts["tr_partners_missing_required_fields"] = tr_partners_missing_required_fields

        # Alert if partner is missing required tax office
        if tr_partners_missing_tax_office := self._l10n_tr_edi_get_partner_tax_office_alert():
            alerts["tr_partners_missing_tax_office"] = tr_partners_missing_tax_office

        # Alert if TR company is missing required tax office
        if tr_companies_missing_tax_office := self._l10n_tr_edi_get_company_tax_office_alert():
            alerts["tr_companies_missing_tax_office"] = tr_companies_missing_tax_office

        # Alert if partner does not use UBL TR e-invoice format or has not checked GİB status
        if tr_partners_invalid_edi_or_status := self.filtered(
            lambda m: (
                m.partner_id.invoice_edi_format != 'ubl_tr'
                or m.partner_id.l10n_tr_edi_customer_status == 'not_checked'
            )
        ).partner_id:
            alerts["tr_partners_invalid_edi_or_status"] = {
                'level': 'danger',
                "message": self.env._(
                    "The following partner(s) either do not have the e-invoice format UBL TR 1.2 "
                    "or have not checked their GİB Status"
                ),
                "action_text": _("View Partner(s)"),
                "action": tr_partners_invalid_edi_or_status._get_records_action(
                    name=self.env._("Check e-Invoice Format or GİB Status on Partner(s)"
                )),
            }

        if invalid_negative_lines := self.filtered(
            lambda move: move._l10n_tr_edi_check_negative_lines(),
        ):
            alerts["critical_invalid_negative_lines"] = {
                "level": "danger",
                "message": self.env._("A Turkish e-Invoice cannot contain a negative quantity or a negative price on its lines."),
                "action_text": _("View Invoice(s)"),
                "action": invalid_negative_lines._get_records_action(name=_("Check data on Invoice(s)")),
            }

        if lines_missing_taxes_moves := self.filtered(
            lambda move: move._l10n_tr_edi_check_lines_missing_taxes(),
        ):
            alerts['tr_lines_missing_taxes'] = {
                'level': 'danger',
                'message': self.env._("Cannot send the e-Invoice: one or more line items are missing a tax rate."),
                'action_text': self.env._("View Invoice(s)"),
                'action': lines_missing_taxes_moves._get_records_action(name=self.env._("Check taxes on Invoice(s)")),
            }

        if moves_with_invalid_name := self.filtered(lambda move: not _is_valid_gib_name(move)):
            alerts['tr_moves_with_invalid_name'] = {
                'level': 'danger',
                'message': _(
                    "The invoice name must follow the GİB format: 3 alphanumeric characters, "
                    "followed by the year, and then a sequential number. Example: INV/2025/000001",
                ),
                'action_text': _("View Invoice(s)"),
                'action': moves_with_invalid_name._get_records_action(name=_("Check name on Invoice(s)")),
            }

        if public_spending_units_missing_vat := self.l10n_tr_public_spending_unit_id.filtered(lambda rec:
            not rec.has_vat
            or not rec.street
            or not rec.city
            or not rec.state_id
            or not rec.country_id,
        ):
            alerts['tr_public_spending_units_missing_vat'] = {
                'level': 'danger',
                'message': self.env._("For Public Sector e-Invoices, the Public Spending Unit must have a valid address and Tax ID defined."),
                'action_text': self.env._("View Partner(s)"),
                'action': public_spending_units_missing_vat._get_records_action(name=self.env._("Check VAT on Partner(s)")),
            }

        exemption_702 = self.env['account.chart.template'].ref('l10n_tr_edi.tax_code_702')
        # Warning alert if a line has no product and is missing CTSP Number
        tr_export_moves = self.filtered(
            lambda m: m.l10n_tr_is_export_invoice or m.l10n_tr_exemption_code_id == exemption_702,
        )
        if non_eligible_tr_lines := tr_export_moves.invoice_line_ids.filtered(
            lambda line: line.display_type == 'product' and not (line.product_id or line.l10n_tr_ctsp_number),
        ):
            alerts['l10n_tr_non_eligible_products'] = {
                'message': self.env._(
                    "The following products are missing a CTSP Number:\n%(products)s\n",
                    products="\n".join(f"- {line.display_name}" for line in non_eligible_tr_lines),
                ),
                'level': 'warning',
                'action_text': self.env._("View Product(s)"),
                'action': non_eligible_tr_lines._get_records_action(
                    name=self.env._("Check Products"),
                ),
            }

        if moves_with_missing_line_codes := self.invoice_line_ids.filtered(
            lambda ml: ml.move_id.l10n_tr_exemption_code_id == exemption_702 and not ml.l10n_tr_customer_line_code,
        ):
            alerts['l10n_tr_moves_with_missing_line_codes'] = {
                'message': _(
                    "For Registered for Export type invoices with a 702 reason code, the Customer "
                    "Line Code must be filled in per product in the invoice lines.",
                ),
                'level': 'danger',
                'action_text': _("View Invoice(s)"),
                'action': moves_with_missing_line_codes.move_id._get_records_action(
                    name=_("Check Invoice(s)"),
                ),
            }

        if (
            invalid_invoice_references
            := self._l10n_tr_edi_check_invalid_invoice_reference()
        ):
            alerts["tr_moves_with_invalid_invoice_reference"] = {
                "level": "danger",
                "message": _(
                    "The credit notes must have a valid reference to the original invoice in the reference field"
                ),
                "action_text": _("Check reference on Invoice(s)"),
                "action": invalid_invoice_references._get_records_action(
                    name=_("Check reference on Credit Note(s)")
                ),
            }

        if invalid_type_invoices := self.filtered(
            lambda r: (r.l10n_tr_gib_invoice_type in GIB_RETURN_INVOICE_TYPES) != (r.move_type == "out_refund")
        ):
            alerts["tr_moves_with_invalid_type"] = {
                "level": "danger",
                "message": _(
                    "Type 'Return' and 'Withholding Return' should only be used for Credit Notes"
                ),
                "action_text": _("Check invoice type"),
                "action": invalid_type_invoices._get_records_action(
                    name=_("Check Invoice Type")
                ),
            }

        if missing_withholding_reason := self.filtered(
            lambda r: r.l10n_tr_gib_invoice_type == "TEVKIFAT"
            and not r.l10n_tr_exemption_code_id
        ):
            alerts["tr_moves_without_withholding_reason"] = {
                "level": "danger",
                "message": self.env._("Withholding invoices must specify the GİB withholding reason"),
                "action_text": self.env._("Check withholding reason"),
                "action": missing_withholding_reason._get_records_action(
                    name=self.env._("Check Withholding Reason"),
                ),
            }

        if inconsistent_withholding := self.filtered(lambda m: m._l10n_tr_withholding_is_inconsistent()):
            alerts["tr_moves_with_inconsistent_withholding"] = {
                "level": "danger",
                "message": self.env._("The lines of a withholding invoice must all withhold at the ratio its reason describes"),
                "action_text": self.env._("Check withholding taxes"),
                "action": inconsistent_withholding._get_records_action(
                    name=self.env._("Check Withholding Taxes"),
                ),
            }

        if (
            tr_withholding_credit_note_tax_mismatch
            := self._l10n_tr_withholding_credit_note_tax_mismatch()
        ):
            alerts["tr_withholding_credite_note_tax_mismatch"] = (
                tr_withholding_credit_note_tax_mismatch
            )

        if tr_credit_note_invoice_not_sent := self.filtered(
            lambda r: r.move_type == "out_refund"
            and r.reversed_entry_id
            and r.reversed_entry_id.l10n_tr_edi_send_status
            not in {"sent", "waiting", "succeed"}
        ):
            alerts["tr_credit_note_invoice_not_sent"] = {
                "level": "danger",
                "message": self.env._(
                    "Return invoices can only be sent if the original invoice has already been successfully sent"
                ),
                "action_text": self.env._("View Invoice(s)"),
                "action": tr_credit_note_invoice_not_sent.reversed_entry_id._get_records_action(
                    name=self.env._("View Invoice(s)")
                ),
            }
        return alerts

    def _l10n_tr_withholding_is_inconsistent(self):
        self.ensure_one()
        if self.l10n_tr_gib_invoice_type not in {"TEVKIFAT", "TEVKIFATIADE"}:
            return False
        if not self.l10n_tr_withholding_ratio:
            # nothing withholds, or the lines disagree
            return True
        if self.l10n_tr_gib_invoice_type == "TEVKIFATIADE":
            # a return has no reason of its own
            return False
        return bool(self.l10n_tr_exemption_code_id) and not self._l10n_tr_reason_is_consistent()

    def _l10n_tr_withholding_credit_note_tax_mismatch(self):
        errors = defaultdict(defaultdict)
        for invoice in self.filtered(
            lambda r: r.country_code == "TR"
            and r.move_type == "out_refund"
            and r.l10n_tr_gib_invoice_type == "TEVKIFATIADE"
        ):
            for line in invoice.invoice_line_ids:
                tax_amount = line.price_total - line.price_subtotal
                expected_percentage = (line.l10n_tr_original_quantity and line.quantity / line.l10n_tr_original_quantity) or 0
                expected_tax_amount = expected_percentage * line.l10n_tr_original_tax_without_withholding
                if float_compare(tax_amount, expected_tax_amount, line.currency_id.decimal_places) != 0:
                    errors[invoice.name][line.product_id.name] = f"{line.currency_id.format(tax_amount)} != {line.currency_id.format(expected_tax_amount)}"

        if not errors:
            return ""

        error_message = _("For withholding return invoices, the tax amount is expected to be the same percentage as the returned quantity.\n"
                            "The following mismatch was found:\n")
        for invoice, lines in errors.items():
            for line, error in lines.items():
                error_message += "- [%s] - %s: %s\n" % (invoice, line, error)

        error_message += _("Make sure the price and taxes match the original invoice.")
        return {
            'level': 'danger',
            'message': error_message,
            'action_text': _("Check Tax Amounts on Credit Note(s)"),
            'action': self._get_records_action(name=_("Check Tax Amounts on Credit Note(s)")),
        }

    def _l10n_tr_edi_get_partner_address_alert(self):
        if tr_partners_missing_required_fields := self.filtered(
            lambda m: (
                not m.l10n_tr_is_export_invoice
                and (
                    not m.partner_id.vat
                    or not m.partner_id.street
                    or not m.partner_id.city
                    or not m.partner_id.state_id
                    or not m.partner_id.country_id
                )
            ),
        ).partner_id:
            return {
                "message": _("The following partner(s) are missing at least one of these fields: Tax ID, Street, City, State or Country"),
                "action_text": _("View Partner(s)"),
                "action": tr_partners_missing_required_fields._get_records_action(name=_("Check Tax ID, City, Street, State, and Country or Partner(s)")),
                "level": "danger",
            }
        return {}

    def _l10n_tr_edi_get_partner_tax_office_alert(self):
        if tr_einvoice_partners_missing_ref := self.partner_id.filtered(
            lambda p: p.l10n_tr_edi_customer_status == 'einvoice' and not p.l10n_tr_tax_office_id,
        ):
            return {
                'message': self.env._("The Tax Office is not set on the following TR Partner(s)."),
                'action_text': self.env._("View Partner(s)"),
                'action': tr_einvoice_partners_missing_ref._get_records_action(
                    name=self.env._("Check reference on Partner(s)"),
                ),
                'level': 'danger',
            }
        return {}

    def _l10n_tr_edi_get_company_tax_office_alert(self):
        if tr_companies_missing_tax_office := self.company_id.filtered(
            lambda c: (not c.l10n_tr_tax_office_id and c.country_code == 'TR'),
        ):
            return {
                'message': self.env._("The Tax Office is not set on the following TR Company(s)."),
                'action_text': self.env._("View Company(s)"),
                'action': tr_companies_missing_tax_office._get_records_action(
                    name=self.env._("TR Company(s)"),
                ),
                'level': 'danger',
            }
        return {}

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
                  FROM l10n_tr_edi_invoice_sequence l10n_tr_series
                 WHERE l10n_tr_series.journal_id = %(journal_id)s
            ), ARRAY[]::text[]))
            """,
            condition=condition,
            journal_id=self.journal_id.id,
        )

    def _get_starting_sequence(self):
        """
        Generate a valid name for credit notes.

        The GİB requires invoice names in the format:
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

    def _l10n_tr_edi_send(self, xml_file):
        """Send the UBL-TR document of this invoice to the GİB.

        A failed send records no e-Document: the error reaches the user and the invoice stays unsent, so it
        can be corrected and sent again. The `error` state is kept for a rejection reported by the GİB.

        :param xml_file: the UBL-TR XML, as a named file-like object.
        :return: the error messages, empty when the document was sent.
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._l10n_tr_edi_send_document(xml_file)
        except UserError as error:
            return [str(error)]
        return []

    def _l10n_tr_edi_send_document(self, xml_file):
        """Send the UBL-TR document through the company's e-Document provider, raising on failure.

        Provider modules override this when the company uses them.

        :param xml_file: the UBL-TR XML, as a named file-like object.
        """
        self.ensure_one()
        raise UserError(self.env._("No e-Document provider is set on %s.", self.company_id.display_name))

    def _l10n_tr_edi_get_provider(self):
        """Return the provider this move's e-Document was sent through, or the company's provider when
        the move has no e-Document yet."""
        self.ensure_one()
        if document := self.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type != 'commercial_response')[:1]:
            return document.provider
        return self.company_id.l10n_tr_edi_provider

    def action_l10n_tr_edi_fetch_status(self):
        self._l10n_tr_edi_fetch_status()

    def _l10n_tr_edi_fetch_status(self):
        """Update the GİB state of these moves' e-Documents from the provider each one was sent through."""
        for provider, moves in self.grouped(lambda move: move._l10n_tr_edi_get_provider()).items():
            moves._l10n_tr_edi_fetch_status_documents(provider)

    def _l10n_tr_edi_fetch_status_documents(self, provider):
        """Update the e-Document state of these moves, all sent through `provider`.

        Provider modules override this for the documents they hold. Without a provider there is
        nobody to ask, so nothing is updated.

        :param provider: the provider the moves' e-Documents were sent through.
        """

    @api.depends('state', 'move_type', 'l10n_tr_edi_document_ids.document_type', 'l10n_tr_edi_document_ids.state')
    def _compute_l10n_tr_edi_can_cancel(self):
        for move in self:
            move.l10n_tr_edi_can_cancel = bool(move._l10n_tr_edi_get_cancellable_document())

    def _l10n_tr_edi_get_cancellable_document(self):
        """Return this invoice's e-Archive that can still be cancelled at the GİB: sent, and neither rejected nor
        already cancelled. Only an e-Archive can be cancelled, and its e-Document says what was sent, whatever the
        customer's GİB status is today."""
        self.ensure_one()
        if self.state != 'posted' or self.move_type != 'out_invoice':
            return self.env['l10n_tr_edi.document']
        return self.l10n_tr_edi_document_ids.filtered(
            lambda d: d.document_type == 'earchive' and d.state in {'sent', 'waiting', 'accepted'},
        )[:1]

    def action_l10n_tr_edi_request_cancel(self):
        self._l10n_tr_edi_cancel()

    def _l10n_tr_edi_cancel(self):
        """Cancel this sent e-Archive invoice at the GİB, through the provider it was sent with."""
        self.ensure_one()
        if not (document := self._l10n_tr_edi_get_cancellable_document()):
            raise UserError(self.env._("Only e-Archive invoices that have been sent successfully can be cancelled."))

        self._l10n_tr_edi_cancel_document(document.provider)
        self.state = 'cancel'
        self._l10n_tr_edi_set_document_state('cancelled', document.provider)

    def _l10n_tr_edi_cancel_document(self, provider):
        """Request the cancellation of this move's e-Archive from `provider`, raising on failure.

        Provider modules override this for the documents they hold.

        :param provider: the provider the move's e-Archive was sent through.
        """
        self.ensure_one()
        raise UserError(self.env._("No e-Document provider can cancel %s.", self.display_name))

    def l10n_tr_action_fetch_ticarifatura_response(self):
        self.ensure_one()

        if self.move_type not in {"out_invoice", "in_invoice"} or self.l10n_tr_gib_invoice_scenario != "TICARIFATURA":
            raise UserError(self.env._("This action is only available for Commercial Invoices/Bills."))
        if self.l10n_tr_edi_send_status in {"commercial_approved", "commercial_answered_automatically", "commercial_rejected"}:
            raise UserError(self.env._("The response has already been received for this invoice."))
        if self.l10n_tr_edi_send_status != "succeed":
            raise UserError(self.env._("The invoice is not approved by the GİB yet."))

        return self._l10n_tr_edi_fetch_status()

    def l10n_tr_action_approve_ticarifatura(self):
        self.ensure_one()
        return self.env['l10n_tr.ticarifatura.response.wizard']._get_records_action(
            name=self.env._('Accept Bill'),
            target='new',
            context={
                **self.env.context,
                'default_move_id': self.id,
                'default_response_code': 'approved',
            },
        )

    def l10n_tr_action_reject_ticarifatura(self):
        self.ensure_one()
        return self.env['l10n_tr.ticarifatura.response.wizard']._get_records_action(
            name=self.env._('Reject Bill'),
            target='new',
            context={
                **self.env.context,
                'default_move_id': self.id,
                'default_response_code': 'rejected',
            },
        )

    def _l10n_tr_action_send_ticarifatura_response(self, answer_code="approved", rejection_note=""):
        self.ensure_one()
        if (
            self.move_type != "in_invoice"
            or self.l10n_tr_gib_invoice_scenario != "TICARIFATURA"
        ):
            raise UserError(
                self.env._("This action is only available for commercial bills.")
            )
        if self.l10n_tr_edi_send_status != "succeed":
            raise UserError(self.env._("The bill must be in 'Successful' status before sending a response."))

        provider = self._l10n_tr_edi_get_provider()
        if (result := self._l10n_tr_edi_send_ticarifatura_response(provider, answer_code, rejection_note)) is not True:
            # Not recorded by the provider: show what it returned instead, such as the answer it already holds.
            return result or True
        self._l10n_tr_edi_set_document_state(
            COMMERCIAL_ANSWER_TO_DOCUMENT_STATE[answer_code], provider, document_type='commercial_response',
        )
        if answer_code == "rejected":
            self._l10n_tr_action_process_rejected_ticarifatura(rejection_note)
        return True

    def _l10n_tr_edi_send_ticarifatura_response(self, provider, answer_code, rejection_note):
        """Send the answer to this received commercial bill through `provider`, raising on failure.

        Provider modules override this for the bills they hold.

        :param provider: the provider the bill was received through.
        :param answer_code: 'approved' or 'rejected'.
        :param rejection_note: why the bill is rejected.
        :return: True when the provider recorded the answer, else what to show the user instead.
        """
        self.ensure_one()
        raise UserError(self.env._("No e-Document provider is set on %s.", self.company_id.display_name))

    def _l10n_tr_action_process_rejected_ticarifatura(self, rejection_note):
        self.ensure_one()
        responder = self.partner_id if self.move_type == "out_invoice" else self.company_id
        self.message_post(
            body=Markup("""
                <div class="border-start border-danger border-3 ps-3 py-2 bg-opacity-10 rounded">
                    <strong class="text-danger">❌ Rejected</strong>
                    <p class="mb-0 mt-1">
                        <strong>Responder:</strong> %s <br/>
                        <strong>Reason:</strong> %s
                    </p>
                </div>
            """)
            % (
                responder.name,
                rejection_note,
            ),
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )
        self._l10n_tr_edi_fetch_rejected_ticarifatura_documents(self._l10n_tr_edi_get_provider())
        self.filtered(lambda m: m.state == "posted").button_draft()
        self.button_cancel()

    def _l10n_tr_edi_fetch_rejected_ticarifatura_documents(self, provider):
        """Fetch from `provider` the documents of this commercial invoice updated by its rejection, such as its PDF.

        Provider modules override this for the invoices they hold.

        :param provider: the provider the invoice was exchanged through.
        """

    def _l10n_tr_edi_fetch_documents(self, document_type, journal_type):
        """Import the GİB documents not yet in Odoo, for each Turkish company from its provider.

        :param document_type: the `l10n_tr_edi.document` type to fetch, 'einvoice' or 'earchive'.
        :param journal_type: 'purchase' for the bills received, 'sale' for the invoices issued outside Odoo.
        """
        for company in self.env.companies:
            if company.country_code == 'TR' and company.l10n_tr_edi_provider:
                self.with_company(company)._l10n_tr_edi_fetch_provider_documents(
                    company.l10n_tr_edi_provider, document_type, journal_type,
                )

    def _l10n_tr_edi_fetch_provider_documents(self, provider, document_type, journal_type):
        """Import the GİB documents not yet in Odoo from `provider`, for the current company.

        Provider modules override this for their own provider.

        :param provider: the e-Document provider of the current company.
        :param document_type: the `l10n_tr_edi.document` type to fetch, 'einvoice' or 'earchive'.
        :param journal_type: 'purchase' for the bills received, 'sale' for the invoices issued outside Odoo.
        """

    def _l10n_tr_edi_get_document_type(self):
        """Return the kind of e-Document this move is: the one already exchanged, else what it would be sent as."""
        self.ensure_one()
        if document := self.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type in {'einvoice', 'earchive'})[:1]:
            # What was sent stays what it is, even if the customer's GİB status changed since.
            return document.document_type
        if (
            self.is_purchase_document(include_receipts=True)
            or self.l10n_tr_is_export_invoice
            or self.partner_id.l10n_tr_edi_customer_status == 'einvoice'
        ):
            return 'einvoice'
        return 'earchive'

    def _l10n_tr_edi_set_document_state(self, state, provider, document_type=None, message=None):
        """Record the GİB state of one of this move's e-Documents, creating the document if needed.

        :param state: the new `l10n_tr_edi.document` state.
        :param provider: the integrator that reported the state.
        :param document_type: the document to update, the move's own e-Invoice or e-Archive if not given.
        :param message: the error or information that comes with the state, replacing the previous one.
        :return: the updated or created document.
        """
        self.ensure_one()
        document_type = document_type or self._l10n_tr_edi_get_document_type()
        if document := self.l10n_tr_edi_document_ids.filtered(lambda d: d.document_type == document_type)[:1]:
            document.write({'state': state, 'provider': provider, 'message': message})
            return document
        return self.env['l10n_tr_edi.document'].create({
            'move_id': self.id,
            'company_id': self.company_id.id,
            'document_type': document_type,
            'provider': provider,
            'state': state,
            'uuid': self.l10n_tr_edi_uuid if document_type != 'commercial_response' else False,
            'message': message,
        })

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _l10n_tr_types_to_update_status(self):
        return ['out_invoice', 'in_invoice']

    def _cron_l10n_tr_edi_fetch_einvoice_purchase_documents(self):
        self._l10n_tr_edi_fetch_documents('einvoice', 'purchase')

    def _cron_l10n_tr_edi_fetch_einvoice_sale_documents(self):
        self._l10n_tr_edi_fetch_documents('einvoice', 'sale')

    def _cron_l10n_tr_edi_fetch_earchive_sale_documents(self):
        self._l10n_tr_edi_fetch_documents('earchive', 'sale')

    def _cron_l10n_tr_edi_fetch_status(self):
        invoices_to_update = self.env['account.move'].search([
            ('l10n_tr_edi_send_status', 'in', ['waiting', 'sent', 'unknown']),
            ('move_type', 'in', self._l10n_tr_types_to_update_status()),
        ])
        invoices_to_update._l10n_tr_edi_fetch_status()
