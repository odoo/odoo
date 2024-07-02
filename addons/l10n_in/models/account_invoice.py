# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.tools.image import image_data_uri


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
            ('uin_holders', 'UIN Holders'),
        ], string="GST Treatment", compute="_compute_l10n_in_gst_treatment", store=True, readonly=False, copy=True, precompute=True)
    l10n_in_state_id = fields.Many2one('res.country.state', string="Place of supply", compute="_compute_l10n_in_state_id", store=True, readonly=False)
    l10n_in_gstin = fields.Char(string="GSTIN")
    # For Export invoice this data is need in GSTR report
    l10n_in_shipping_bill_number = fields.Char('Shipping bill number')
    l10n_in_shipping_bill_date = fields.Date('Shipping bill date')
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', 'Port code')
    l10n_in_reseller_partner_id = fields.Many2one('res.partner', 'Reseller', domain=[('vat', '!=', False)], help="Only Registered Reseller")
    l10n_in_journal_type = fields.Selection(string="Journal Type", related='journal_id.type')

    @api.depends('partner_id', 'partner_id.l10n_in_gst_treatment', 'state')
    def _compute_l10n_in_gst_treatment(self):
        indian_invoice = self.filtered(lambda m: m.country_code == 'IN')
        for record in indian_invoice:
            if record.state == 'draft':
                gst_treatment = record.partner_id.l10n_in_gst_treatment
                if not gst_treatment:
                    gst_treatment = 'unregistered'
                    if record.partner_id.country_id.code == 'IN' and record.partner_id.vat:
                        gst_treatment = 'regular'
                    elif record.partner_id.country_id and record.partner_id.country_id.code != 'IN':
                        gst_treatment = 'overseas'
                record.l10n_in_gst_treatment = gst_treatment
        (self - indian_invoice).l10n_in_gst_treatment = False

    @api.depends('partner_id', 'partner_shipping_id', 'company_id')
    def _compute_l10n_in_state_id(self):
        for move in self:
            if move.country_code == 'IN' and move.journal_id.type == 'sale':
                partner_state = (
                    move.partner_id.commercial_partner_id == move.partner_shipping_id.commercial_partner_id
                    and move.partner_shipping_id.state_id
                    or move.partner_id.state_id
                )
                if not partner_state:
                    partner_state = move.partner_id.commercial_partner_id.state_id or move.company_id.state_id
                country_code = partner_state.country_id.code or move.country_code
                if country_code == 'IN':
                    move.l10n_in_state_id = partner_state
                else:
                    move.l10n_in_state_id = self.env.ref('l10n_in.state_in_oc', raise_if_not_found=False)
            elif move.country_code == 'IN' and move.journal_id.type == 'purchase':
                move.l10n_in_state_id = move.company_id.state_id
            else:
                move.l10n_in_state_id = False

    @api.onchange('name')
    def _onchange_name_warning(self):
        if self.country_code == 'IN' and self.journal_id.type == 'sale' and self.name and (len(self.name) > 16 or not re.match(r'^[a-zA-Z0-9-\/]+$', self.name)):
            return {'warning': {
                'title' : _("Invalid sequence as per GST rule 46(b)"),
                'message': _(
                    "The invoice number should not exceed 16 characters\n"
                    "and must only contain '-' (hyphen) and '/' (slash) as special characters"
                )
            }}
        return super()._onchange_name_warning()

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
        for move in posted.filtered(lambda m: m.country_code == 'IN' and m.is_sale_document()):
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
            if not move.l10n_in_gstin and move.l10n_in_gst_treatment in ['regular', 'composition', 'special_economic_zone', 'deemed_export']:
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

    def _generate_qr_code(self, silent_errors=False):
        self.ensure_one()
        if self.company_id.country_code == 'IN':
            payment_url = 'upi://pay?pa=%s&pn=%s&am=%s&tr=%s&tn=%s' % (
                self.company_id.l10n_in_upi_id,
                self.company_id.name,
                self.amount_residual,
                self.payment_reference or self.name,
                ("Payment for %s" % self.name))
            barcode = self.env['ir.actions.report'].barcode(barcode_type="QR", value=payment_url, width=120, height=120)
            return image_data_uri(base64.b64encode(barcode))
        return super()._generate_qr_code(silent_errors)

    def _l10n_in_get_hsn_summary_table(self):
        self.ensure_one()
        display_uom = self.env.user.has_group('uom.group_uom')

        base_lines = []
        for line in self.invoice_line_ids.filtered(lambda x: x.display_type == 'product'):
            taxes_data = line.tax_ids._convert_to_dict_for_taxes_computation()
            product_values = self.env['account.tax']._eval_taxes_computation_turn_to_product_values(
                taxes_data,
                product=line.product_id,
            )

            base_lines.append({
                'l10n_in_hsn_code': line.l10n_in_hsn_code,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'product_values': product_values,
                'uom': {'id': line.product_uom_id.id, 'name': line.product_uom_id.name},
                'taxes_data': taxes_data,
            })
        return self.env['account.tax']._l10n_in_get_hsn_summary_table(base_lines, display_uom)

    # ------Utils------
    @api.model
    def _l10n_in_prepare_tax_details(self):
        def l10n_in_grouping_key_generator(base_line, tax_values):
            invl = base_line['record']
            tax = tax_values['tax_repartition_line'].tax_id
            tags = tax_values['tax_repartition_line'].tag_ids
            line_code = "other"
            if not invl.currency_id.is_zero(tax_values['tax_amount_currency']):
                if self.env.ref("l10n_in.tax_tag_cess") in tags:
                    if tax.amount_type != "percent":
                        line_code = "cess_non_advol"
                    else:
                        line_code = "cess"
                elif self.env.ref("l10n_in.tax_tag_state_cess") in tags:
                    if tax.amount_type != "percent":
                        line_code = "state_cess_non_advol"
                    else:
                        line_code = "state_cess"
                else:
                    for gst in ["cgst", "sgst", "igst"]:
                        if self.env.ref(f"l10n_in.tax_tag_{gst}") in tags:
                            line_code = gst
                        # need to separate rc tax value so it's not pass to other values
                        if self.env.ref(f"l10n_in.tax_tag_{gst}_rc") in tags:
                            line_code = gst + '_rc'
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
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    @api.model
    def _l10n_in_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        value = round(amount, precision_digits)
        # avoid -0.0
        return value or 0.0

    @api.model
    def _get_l10n_in_tax_details_by_line_code(self, tax_details):
        l10n_in_tax_details = {}
        for tax_detail in tax_details.values():
            if tax_detail["tax"].l10n_in_reverse_charge:
                l10n_in_tax_details.setdefault("is_reverse_charge", True)
            l10n_in_tax_details.setdefault("%s_rate" % (tax_detail["line_code"]), tax_detail["tax"].amount)
            l10n_in_tax_details.setdefault("%s_amount" % (tax_detail["line_code"]), 0.00)
            l10n_in_tax_details.setdefault("%s_amount_currency" % (tax_detail["line_code"]), 0.00)
            l10n_in_tax_details["%s_amount" % (tax_detail["line_code"])] += tax_detail["tax_amount"]
            l10n_in_tax_details["%s_amount_currency" % (tax_detail["line_code"])] += tax_detail["tax_amount_currency"]
        return l10n_in_tax_details

    def _l10n_in_is_process_thru_irn(self):
        self.ensure_one()
        return False
