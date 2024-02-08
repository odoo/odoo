# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import re

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.tools import frozendict
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
    l10n_in_hsn_code_warning = fields.Json(compute="_compute_hsn_code_warning")

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

    @api.depends('invoice_line_ids.l10n_in_hsn_code', 'company_id.l10n_in_hsn_code_digit')
    def _compute_hsn_code_warning(self):

        def build_warning(record, action_name, message, views, domain=False):
            return {
                'message': message,
                'action_text': _("View %s", action_name),
                'action': record._get_records_action(name=_("Check %s", action_name), target='current', views=views, domain=domain or [])
            }

        indian_invoice = self.filtered(lambda m: m.country_code == 'IN' and m.move_type != 'entry')
        for move in indian_invoice:
            filtered_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and line.tax_ids and line._origin)
            if move.company_id.l10n_in_hsn_code_digit and filtered_lines:
                lines = self.env['account.move.line']
                for line in filtered_lines:
                    if (line.l10n_in_hsn_code and (not re.match(r'^\d{4}$|^\d{6}$|^\d{8}$', line.l10n_in_hsn_code) or len(line.l10n_in_hsn_code) < int(move.company_id.l10n_in_hsn_code_digit))) or not line.l10n_in_hsn_code:
                        lines |= line._origin

                digit_suffixes = {
                    '4': _("4 digits, 6 digits or 8 digits"),
                    '6': _("6 digits or 8 digits"),
                    '8': _("8 digits")
                }
                msg = _("Ensure that the HSN/SAC Code consists either %s in invoice lines",
                    digit_suffixes.get(move.company_id.l10n_in_hsn_code_digit, _("Invalid HSN/SAC Code digit"))
                )
                move.l10n_in_hsn_code_warning = {
                    'invalid_hsn_code_length': build_warning(
                        message=msg,
                        action_name=_("Journal Items(s)"),
                        record=lines,
                        views=[(self.env.ref("l10n_in.view_move_line_tree_hsn_l10n_in").id, "tree")],
                        domain=[('id', 'in', lines.ids)]
                    )
                } if lines else {}
            else:
                move.l10n_in_hsn_code_warning = {}
        (self - indian_invoice).l10n_in_hsn_code_warning = {}

    def _get_name_invoice_report(self):
        if self.country_code == 'IN':
            # TODO: remove the view mode check in master, only for stable releases
            in_invoice_view = self.env.ref('l10n_in.l10n_in_report_invoice_document_inherit', raise_if_not_found=False)
            if (in_invoice_view and in_invoice_view.sudo().mode == "primary"):
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
        display_uom = self.env.user.user_has_groups('uom.group_uom')
        tag_igst = self.env.ref('l10n_in.tax_tag_igst')
        tag_cgst = self.env.ref('l10n_in.tax_tag_cgst')
        tag_sgst = self.env.ref('l10n_in.tax_tag_sgst')
        tag_cess = self.env.ref('l10n_in.tax_tag_cess')

        def filter_invl_to_apply(invoice_line):
            return bool(invoice_line.l10n_in_hsn_code)

        def grouping_key_generator(base_line, _tax_values):
            # The rate is only for SGST/CGST.
            if base_line['is_refund']:
                tax_rep_field = 'refund_repartition_line_ids'
            else:
                tax_rep_field = 'invoice_repartition_line_ids'
            gst_taxes = base_line['taxes'].flatten_taxes_hierarchy()[tax_rep_field]\
                .filtered(lambda tax_rep: (
                    tax_rep.repartition_type == 'tax'
                    and any(tag in tax_rep.tag_ids for tag in tag_sgst + tag_cgst + tag_igst)
                ))\
                .tax_id

            return {
                'l10n_in_hsn_code': base_line['record'].l10n_in_hsn_code,
                'rate': sum(gst_taxes.mapped('amount')),
                'uom': base_line['record'].product_uom_id,
            }

        aggregated_values = self._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=filter_invl_to_apply,
            grouping_key_generator=grouping_key_generator,
        )

        results_map = {}
        has_igst = False
        has_gst = False
        has_cess = False
        for grouping_key, tax_details in aggregated_values['tax_details'].items():
            values = results_map.setdefault(grouping_key, {
                'quantity': 0.0,
                'amount_untaxed': tax_details['base_amount_currency'],
                'tax_amounts': defaultdict(lambda: 0.0),
            })

            # Quantity.
            invoice_line_ids = set()
            for invoice_line in tax_details['records']:
                if invoice_line.id not in invoice_line_ids:
                    values['quantity'] += invoice_line.quantity
                    invoice_line_ids.add(invoice_line.id)

            # Tax amounts.
            for tax_details in tax_details['group_tax_details']:
                tax_rep = tax_details['tax_repartition_line']
                if tag_igst in tax_rep.tag_ids:
                    has_igst = True
                    values['tax_amounts'][tag_igst] += tax_details['tax_amount_currency']
                if tag_cgst in tax_rep.tag_ids:
                    has_gst = True
                    values['tax_amounts'][tag_cgst] += tax_details['tax_amount_currency']
                if tag_sgst in tax_rep.tag_ids:
                    has_gst = True
                    values['tax_amounts'][tag_sgst] += tax_details['tax_amount_currency']
                if tag_cess in tax_rep.tag_ids:
                    has_cess = True
                    values['tax_amounts'][tag_cess] += tax_details['tax_amount_currency']

        # In case of base_line with HSN code but no taxes, an entry in results_map should be created.
        for base_line, _to_update_vals, _tax_values_list in aggregated_values['to_process']:
            if base_line['taxes']:
                continue

            grouping_key = frozendict(grouping_key_generator(base_line, None))
            results = results_map.setdefault(grouping_key, {
                'quantity': 0.0,
                'amount_untaxed': 0.0,
                'tax_amounts': defaultdict(lambda: 0.0),
            })
            results['quantity'] += base_line['quantity']
            results['amount_untaxed'] += base_line['price_subtotal']

        nb_columns = 5
        if has_igst:
            nb_columns += 1
        if has_gst:
            nb_columns += 2
        if has_cess:
            nb_columns += 1

        items = []
        for grouping_key, values in results_map.items():
            items.append({
                'l10n_in_hsn_code': grouping_key['l10n_in_hsn_code'],
                'quantity': values['quantity'],
                'uom': grouping_key['uom'],
                'rate': grouping_key['rate'],
                'amount_untaxed': values['amount_untaxed'],
                'tax_amount_igst': values['tax_amounts'].get(tag_igst, 0.0),
                'tax_amount_cgst': values['tax_amounts'].get(tag_cgst, 0.0),
                'tax_amount_sgst': values['tax_amounts'].get(tag_sgst, 0.0),
                'tax_amount_cess': values['tax_amounts'].get(tag_cess, 0.0),
            })

        return {
            'has_igst': has_igst,
            'has_gst': has_gst,
            'has_cess': has_cess,
            'nb_columns': nb_columns,
            'display_uom': display_uom,
            'items': items,
        }
