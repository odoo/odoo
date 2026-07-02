import logging
import re

from contextlib import contextmanager
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.tools.float_utils import json_float_round
from odoo.tools.image import image_data_uri
from odoo.addons.l10n_in.models.iap_account import IAP_SERVICE_NAME

EDI_CANCEL_REASON = {
    # Same for both e-way bill and IRN
    '1': "Duplicate",
    '2': "Data Entry Mistake",
    '3': "Order Cancelled",
    '4': "Others",
}
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_gst_treatment = fields.Selection(
        selection=[
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
            ('uin_holders', 'UIN Holders'),
        ],
        string="GST Treatment",
        compute="_compute_l10n_in_gst_treatment",
        store=True,
        readonly=False,
        copy=True,
        precompute=True
    )
    l10n_in_state_id = fields.Many2one(
        comodel_name='res.country.state',
        string="Place of supply",
        compute="_compute_l10n_in_state_id",
        store=True,
        copy=True,
        readonly=False,
        precompute=True
    )
    l10n_in_gstin = fields.Char(string="GSTIN")
    # For Export invoice this data is need in GSTR report
    l10n_in_shipping_bill_number = fields.Char('Shipping bill number')
    l10n_in_shipping_bill_date = fields.Date('Shipping bill date')
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', 'Port code')
    l10n_in_reseller_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Reseller",
        domain=[('vat', '!=', False)],
        help="Only Registered Reseller"
    )
    l10n_in_journal_type = fields.Selection(string="Journal Type", related='journal_id.type')
    l10n_in_warning = fields.Json(compute="_compute_l10n_in_warning")
    l10n_in_is_gst_registered_enabled = fields.Boolean(related='company_id.l10n_in_is_gst_registered')
    l10n_in_tds_deduction = fields.Selection(related='commercial_partner_id.l10n_in_pan_entity_id.tds_deduction', string="TDS Deduction")

    # withholding related fields
    l10n_in_tds_feature_enabled = fields.Boolean(related='company_id.l10n_in_tds_feature')
    l10n_in_tcs_feature_enabled = fields.Boolean(related='company_id.l10n_in_tcs_feature')

    # gstin_status related field
    l10n_in_partner_gstin_status = fields.Boolean(
        string="GST Status",
        compute="_compute_l10n_in_partner_gstin_status_and_date",
    )
    l10n_in_show_gstin_status = fields.Boolean(compute="_compute_l10n_in_show_gstin_status")
    l10n_in_gstin_verified_date = fields.Date(compute="_compute_l10n_in_partner_gstin_status_and_date")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('partner_id')
    def _compute_l10n_in_gst_treatment(self):
        for invoice in self.filtered(lambda m: m.country_code == 'IN' and m.state == 'draft'):
            partner = invoice.partner_id
            invoice.l10n_in_gst_treatment = (
                partner.l10n_in_gst_treatment
                or (
                    'overseas' if partner.country_id and partner.country_id.code != 'IN'
                    else partner.check_vat_in(partner.vat) and 'regular' or 'consumer'
                )
            )

    @api.depends('partner_id', 'partner_shipping_id', 'company_id')
    def _compute_l10n_in_state_id(self):
        foreign_state = self.env.ref('l10n_in.state_in_oc', raise_if_not_found=False)
        for move in self:
            if move.country_code == 'IN' and move.is_sale_document(include_receipts=True):
                partner = (
                    move.partner_id.commercial_partner_id == move.partner_shipping_id.commercial_partner_id
                    and move.partner_shipping_id
                    or move.partner_id
                )
                if partner.country_id and partner.country_id.code != 'IN':
                    move.l10n_in_state_id = foreign_state
                    continue
                partner_state = partner.state_id or move.partner_id.commercial_partner_id.state_id or move.company_id.state_id
                country_code = partner_state.country_id.code or move.country_code
                move.l10n_in_state_id = partner_state if country_code == 'IN' else foreign_state
            elif move.country_code == 'IN' and move.journal_id.type == 'purchase':
                move.l10n_in_state_id = move.company_id.state_id
            else:
                move.l10n_in_state_id = False

    @api.depends('l10n_in_state_id', 'l10n_in_gst_treatment')
    def _compute_fiscal_position_id(self):
        foreign_country = self.env['res.country'].new({'name': 'Not India', 'code': '!!'})
        foreign_state = self.env['res.country.state'].new({'country_id': foreign_country})

        def _get_fiscal_state(move):
            """
            Maps each move to its corresponding fiscal state based on its type,
            fiscal conditions, and the state of the associated partner or company.
            """

            if (
                move.country_code != 'IN'
                or not move.is_invoice(include_receipts=True)
                # Partner's FP takes precedence through super
                or move.partner_shipping_id.property_account_position_id
                or move.partner_id.property_account_position_id
            ):
                return False
            elif move.l10n_in_gst_treatment == 'special_economic_zone':
                # Special Economic Zone
                return self.env.ref('l10n_in.state_in_oc')
            elif move.is_sale_document(include_receipts=True):
                # In Sales Documents: Compare place of supply with company state
                return move.l10n_in_state_id if move.l10n_in_state_id.l10n_in_tin != '96' else foreign_state
            elif move.is_purchase_document(include_receipts=True) and move.partner_id.country_id.code == 'IN':
                # In Purchases Documents: Compare place of supply with vendor state
                pos_state_id = move.l10n_in_state_id
                if pos_state_id.l10n_in_tin == '96':
                    return pos_state_id
                elif pos_state_id == move.partner_id.state_id:
                    # Intra-State: Group by state matching the company's state.
                    return move.company_id.state_id
                elif pos_state_id != move.partner_id.state_id:
                    # Inter-State: Group by state that doesn't match the company's state.
                    return (
                        pos_state_id == move.company_id.state_id
                        and move.partner_id.state_id
                        or pos_state_id
                    )
            return False

        FiscalPosition = self.env['account.fiscal.position']
        for state_id, moves in self.grouped(_get_fiscal_state).items():
            if state_id:
                virtual_partner = self.env['res.partner'].new({
                    'state_id': state_id.id,
                    'country_id': state_id.country_id.id,
                })
                # Group moves by company to avoid multi-company conflicts
                for company_id, company_moves in moves.grouped('company_id').items():
                    company_moves.fiscal_position_id = FiscalPosition.with_company(
                        company_id
                    )._get_fiscal_position(virtual_partner)
            else:
                super(AccountMove, moves)._compute_fiscal_position_id()

    @api.onchange('name')
    def _onchange_name_warning(self):
        if (
            self.country_code == 'IN'
            and self.company_id.l10n_in_is_gst_registered
            and self.journal_id.type == 'sale'
            and self.name
            and (len(self.name) > 16 or not re.match(r'^[a-zA-Z0-9-\/]+$', self.name))
        ):
            return {'warning': {
                'title' : _("Invalid sequence as per GST rule 46(b)"),
                'message': _(
                    "The invoice number should not exceed 16 characters\n"
                    "and must only contain '-' (hyphen) and '/' (slash) as special characters"
                )
            }}
        return super()._onchange_name_warning()

    @api.depends(
        'invoice_line_ids.l10n_in_hsn_code',
        'company_id.l10n_in_hsn_code_digit',
        'invoice_line_ids.tax_ids',
        'commercial_partner_id.l10n_in_pan_entity_id',
        'invoice_line_ids.price_total'
    )
    def _compute_l10n_in_warning(self):
        indian_invoice = self.filtered(lambda m: m.country_code == 'IN' and m.move_type != 'entry')
        line_filter_func = lambda line: line.display_type == 'product' and line.tax_ids and line._origin
        _xmlid_to_res_id = self.env['ir.model.data']._xmlid_to_res_id
        for move in indian_invoice:
            warnings = {}
            company = move.company_id
            action_name = _("Journal Item(s)")
            action_text = _("View Journal Item(s)")
            if (
                company.l10n_in_is_gst_registered
                and company.l10n_in_hsn_code_digit
                and (filtered_lines := move.invoice_line_ids.filtered(line_filter_func))
            ):
                lines = self.env['account.move.line']
                for line in filtered_lines:
                    hsn_code = line.l10n_in_hsn_code
                    if (
                        not hsn_code
                        or (
                            not re.match(r'^\d{4}$|^\d{6}$|^\d{8}$', hsn_code)
                            or len(hsn_code) < int(company.l10n_in_hsn_code_digit)
                        )
                    ):
                        lines |= line._origin

                if lines:
                    digit_suffixes = {
                        '4': _("4 digits, 6 digits or 8 digits"),
                        '6': _("6 digits or 8 digits"),
                        '8': _("8 digits")
                    }
                    msg = _(
                        "Ensure that the HSN/SAC Code consists either %s in invoice lines",
                        digit_suffixes.get(company.l10n_in_hsn_code_digit, _("Invalid HSN/SAC Code digit"))
                    )
                    warnings['invalid_hsn_code_length'] = {
                        'message': msg,
                        'action': lines._get_records_action(
                            name=action_name,
                            views=[(_xmlid_to_res_id("l10n_in.view_move_line_tree_hsn_l10n_in"), "list")],
                            domain=[('id', 'in', lines.ids)]
                        ),
                        'action_text': action_text,
                    }

            move.l10n_in_warning = warnings
        (self - indian_invoice).l10n_in_warning = {}

    @api.depends('partner_id', 'state', 'payment_state', 'l10n_in_gst_treatment')
    def _compute_l10n_in_show_gstin_status(self):
        indian_moves = self.filtered(
            lambda m: m.country_code == 'IN' and m.company_id.l10n_in_gstin_status_feature
        )
        (self - indian_moves).l10n_in_show_gstin_status = False
        for move in indian_moves:
            move.l10n_in_show_gstin_status = (
                move.partner_id
                and move.state == 'posted'
                and move.move_type != 'entry'
                and move.payment_state not in ['paid', 'reversed']
                and move.l10n_in_gst_treatment in [
                    'regular',
                    'composition',
                    'special_economic_zone',
                    'deemed_export',
                    'uin_holders'
                ]
            )

    @api.depends('partner_id')
    def _compute_l10n_in_partner_gstin_status_and_date(self):
        for move in self:
            if (
                move.country_code == 'IN'
                and move.company_id.l10n_in_gstin_status_feature
                and move.payment_state not in ['paid', 'reversed']
                and move.state != 'cancel'
            ):
                move.l10n_in_partner_gstin_status = move.partner_id.l10n_in_gstin_verified_status
                move.l10n_in_gstin_verified_date = move.partner_id.l10n_in_gstin_verified_date
            else:
                move.l10n_in_partner_gstin_status = False
                move.l10n_in_gstin_verified_date = False

    def l10n_in_verify_partner_gstin_status(self):
        self.ensure_one()
        return self.with_company(self.company_id).partner_id.action_l10n_in_verify_gstin_status()

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.country_code == 'IN':
            return 'l10n_in.l10n_in_report_invoice_document_inherit'
        return super()._get_name_invoice_report()

    def _post(self, soft=True):
        """Use journal type to define document type because not miss state in any entry including POS entry"""
        posted = super()._post(soft)
        gst_treatment_name_mapping = {k: v for k, v in
                             self._fields['l10n_in_gst_treatment']._description_selection(self.env)}
        for move in posted.filtered(lambda m: m.country_code == 'IN' and m.company_id.l10n_in_is_gst_registered and m.is_sale_document()):
            if move.l10n_in_state_id and not move.l10n_in_state_id.l10n_in_tin:
                raise UserError(_("Please set a valid TIN Number on the Place of Supply %s", move.l10n_in_state_id.name))
            if not move.company_id.state_id:
                msg = _("Your company %s needs to have a correct address in order to validate this invoice.\n"
                "Set the address of your company (Don't forget the State field)", move.company_id.name)
                action = {
                    "view_mode": "form",
                    "res_model": "res.company",
                    "type": "ir.actions.act_window",
                    "res_id" : move.company_id.id,
                    "views": [[self.env.ref("base.view_company_form").id, "form"]],
                }
                raise RedirectWarning(msg, action, _('Go to Company configuration'))
            move.l10n_in_gstin = move.partner_id.vat
            if (
                not move.l10n_in_gstin
                and move.l10n_in_gst_treatment in [
                    'regular',
                    'composition',
                    'special_economic_zone',
                    'deemed_export'
                ]
            ):
                raise ValidationError(_(
                    "Partner %(partner_name)s (%(partner_id)s) GSTIN is required under GST Treatment %(name)s",
                    partner_name=move.partner_id.name,
                    partner_id=move.partner_id.id,
                    name=gst_treatment_name_mapping.get(move.l10n_in_gst_treatment)
                ))
        return posted

    def _l10n_in_get_warehouse_address(self):
        """Return address where goods are delivered/received for Invoice/Bill"""
        # TO OVERRIDE
        self.ensure_one()
        return False

    def _can_be_unlinked(self):
        self.ensure_one()
        return (self.country_code != 'IN' or not self.posted_before) and super()._can_be_unlinked()

    def _generate_qr_code(self, silent_errors=False):
        self.ensure_one()
        if (
            self.company_id.l10n_in_upi_id
            and self.amount_residual
            and self.move_type == 'out_invoice'
        ):
            payment_url = 'upi://pay?pa=%s&pn=%s&am=%s&tr=%s&tn=%s' % (
                self.company_id.l10n_in_upi_id,
                self.company_id.name,
                self.amount_residual,
                self.payment_reference or self.name,
                ("Payment for %s" % self.name))
            barcode = self.env['ir.actions.report'].barcode(barcode_type="QR", value=payment_url, width=120, height=120, quiet=False)
            return image_data_uri(barcode)
        return super()._generate_qr_code(silent_errors)

    def _l10n_in_get_hsn_summary_table(self):
        self.ensure_one()
        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        display_uom = self.env.user.has_group('uom.group_uom')
        return self.env['account.tax']._l10n_in_get_hsn_summary_table(base_lines, display_uom)

    def _l10n_in_get_bill_from_irn(self, irn):
        # TO OVERRIDE
        return False

    # ------Utils------
    @api.model
    def _l10n_in_prepare_tax_details(self):
        def l10n_in_grouping_key_generator(base_line, tax_data):
            invl = base_line['record']
            tax = tax_data['tax']
            if self.l10n_in_gst_treatment in ('overseas', 'special_economic_zone') and all(
                self.env.ref("l10n_in.tax_tag_igst") in rl.tag_ids
                for rl in tax.invoice_repartition_line_ids if rl.repartition_type == 'tax'
            ):
                tax_data['is_reverse_charge'] = False
            tag_ids = tax.invoice_repartition_line_ids.tag_ids.ids
            line_code = "other"
            xmlid_to_res_id = self.env['ir.model.data']._xmlid_to_res_id
            if not invl.currency_id.is_zero(tax_data['tax_amount_currency']):
                if xmlid_to_res_id("l10n_in.tax_tag_cess") in tag_ids:
                    if tax.amount_type != "percent":
                        line_code = "cess_non_advol"
                    else:
                        line_code = "cess"
                elif xmlid_to_res_id("l10n_in.tax_tag_state_cess") in tag_ids:
                    if tax.amount_type != "percent":
                        line_code = "state_cess_non_advol"
                    else:
                        line_code = "state_cess"
                else:
                    for gst in ["cgst", "sgst", "igst"]:
                        if xmlid_to_res_id("l10n_in.tax_tag_%s" % (gst)) in tag_ids:
                            # need to separate rc tax value so it's not pass to other values
                            line_code = f'{gst}_rc' if tax_data['is_reverse_charge'] else gst
            return {
                "tax": tax,
                "base_product_id": invl.product_id,
                "tax_product_id": invl.product_id,
                "base_product_uom_id": invl.product_uom_id,
                "tax_product_uom_id": invl.product_uom_id,
                "line_code": line_code,
            }

        def l10n_in_filter_to_apply(base_line, tax_values):
            return base_line['record'].display_type != 'rounding'

        return self._prepare_invoice_aggregated_taxes(
            filter_tax_values_to_apply=l10n_in_filter_to_apply,
            grouping_key_generator=l10n_in_grouping_key_generator,
        )

    def _get_l10n_in_seller_buyer_party(self):
        self.ensure_one()
        return {
            "seller_details": self.company_id.partner_id,
            "dispatch_details": self._l10n_in_get_warehouse_address() or self.company_id.partner_id,
            "buyer_details": self.partner_id,
            "ship_to_details": self.partner_shipping_id or self.partner_id
        }

    @api.model
    def _l10n_in_extract_digits(self, string):
        if not string:
            return ""
        matches = re.findall(r"\d+", string)
        return "".join(matches)

    @api.model
    def _l10n_in_is_service_hsn(self, hsn_code):
        return self._l10n_in_extract_digits(hsn_code).startswith('99')

    @api.model
    def _l10n_in_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        return json_float_round(amount, precision_digits)

    @api.model
    def _get_l10n_in_tax_details_by_line_code(self, tax_details):
        l10n_in_tax_details = {}
        for tax_detail in tax_details.values():
            if tax_detail["tax"].l10n_in_reverse_charge:
                l10n_in_tax_details.setdefault("is_reverse_charge", True)
            line_code = tax_detail["line_code"]
            l10n_in_tax_details.setdefault("%s_rate" % (line_code), tax_detail["tax"].amount)
            l10n_in_tax_details.setdefault("%s_amount" % (line_code), 0.00)
            l10n_in_tax_details.setdefault("%s_amount_currency" % (line_code), 0.00)
            l10n_in_tax_details["%s_amount" % (line_code)] += tax_detail["tax_amount"]
            l10n_in_tax_details["%s_amount_currency" % (line_code)] += tax_detail["tax_amount_currency"]
        return l10n_in_tax_details

    @api.model
    def _l10n_in_edi_get_iap_buy_credits_message(self):
        url = self.env['iap.account'].get_credits_url(service_name=IAP_SERVICE_NAME)
        return Markup("""<p><b>%s</b></p><p>%s <a href="%s">%s</a></p>""") % (
            _("You have insufficient credits to send this document!"),
            _("Please buy more credits and retry: "),
            url,
            _("Buy Credits")
        )

    def _get_sync_stack(self, container):
        stack, update_containers = super()._get_sync_stack(container)
        if all(move.country_code != 'IN' for move in self):
            return stack, update_containers
        _tax_container, invoice_container, misc_container = update_containers()
        moves = invoice_container['records'] + misc_container['records']
        stack.append((9, self._sync_l10n_in_gstr_section(moves)))
        return stack, update_containers

    @contextmanager
    def _sync_l10n_in_gstr_section(self, moves):
        yield
        tax_tags_dict = self.env['account.move.line']._get_l10n_in_tax_tag_ids()
        # we set the section on the invoice lines
        moves.line_ids._set_l10n_in_gstr_section(tax_tags_dict)

    def _get_l10n_in_invoice_label(self):
        self.ensure_one()
        exempt_types = {'exempt', 'nil_rated', 'non_gst'}
        if self.country_code != 'IN' or not self.is_sale_document(include_receipts=False):
            return
        gst_treatment = self.l10n_in_gst_treatment
        company = self.company_id
        tax_types = set(self.invoice_line_ids.tax_ids.mapped('l10n_in_tax_type'))
        if company.l10n_in_is_gst_registered and tax_types:
            if gst_treatment in ['overseas', 'special_economic_zone']:
                return 'Tax Invoice'
            elif tax_types.issubset(exempt_types):
                return 'Bill of Supply'
            elif tax_types.isdisjoint(exempt_types):
                return 'Tax Invoice'
            elif gst_treatment in ['unregistered', 'consumer']:
                return 'Invoice-cum-Bill of Supply'
        return 'Invoice'
