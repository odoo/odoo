# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.tools.image import image_data_uri

GSTR_SECTION_SELECTION = [
    ('b2b_regular', 'B2B Regular'),
    ('b2b_reverse_charge', 'B2B Reverse Charge'),
    ('b2cl', 'B2CL(Large)'),
    ('expwp', 'Export With Payment'),
    ('expwop', 'Export Without Payment'),
    ('sezwp', 'Special Economic Zone With Payment'),
    ('sezwop', 'Special Economic Zone Without Payment'),
    ('de', 'Deemed Export'),
    ('b2cs', 'B2CS(Others)'),
    ('cdnr', 'Credit/Debit Notes Registered'),
    ('cdnur', 'Credit/Debit Notes Unregistered'),
]


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
    l10n_in_gstr_json = fields.Json(string='GSTR JSON', copy=False)
    l10n_in_gstr_section = fields.Selection(selection=GSTR_SECTION_SELECTION, string="GSTR Section", compute="_compute_gstr_section", store=True, readonly=False)
    has_nil_exempt_nongst = fields.Boolean(
        string='Has Nil Rated, Exempt or Non Gst Supplies',
        compute='_compute_has_nil_exempt_nongst',
        store=True
    )

    @api.depends('invoice_line_ids', 'invoice_line_ids.tax_ids', 'l10n_in_gst_treatment', 'move_type')
    def _compute_has_nil_exempt_nongst(self):
        taxes_tag_ids = self._get_l10n_in_taxes_tags_id_by_name()
        nil_exempt_nongst_tags = [taxes_tag_ids[key] for key in ['exempt', 'nil_rated', 'non_gst_supplies']]
        for record in self:
            record.has_nil_exempt_nongst = record.l10n_in_gst_treatment not in ('overseas', 'special_economic_zone') \
                and record.move_type in ('out_invoice', 'out_refund', 'out_receipt') \
                and any(tag in nil_exempt_nongst_tags for tag in record.invoice_line_ids.tax_tag_ids.ids)

    @api.depends('partner_id', 'invoice_line_ids', 'amount_total', 'invoice_line_ids.tax_ids.l10n_in_reverse_charge',
        'move_type', 'state', 'l10n_in_gst_treatment', 'l10n_in_state_id', 'invoice_line_ids.tax_ids', 'debit_origin_id')
    def _compute_gstr_section(self):
        taxes_tag_ids = self._get_l10n_in_taxes_tags_id_by_name()
        igst_tag_ids = [taxes_tag_ids['base_igst'], taxes_tag_ids['igst']]
        cess_tag_ids = [taxes_tag_ids['base_cess'], taxes_tag_ids['cess']]
        gst_tags = igst_tag_ids + cess_tag_ids + [taxes_tag_ids[key] for key in ['base_sgst', 'sgst', 'base_cgst', 'cgst']]
        nil_and_gst_tags = gst_tags + [taxes_tag_ids[key] for key in ['exempt', 'nil_rated', 'non_gst_supplies']]
        export_tags = igst_tag_ids + [taxes_tag_ids['zero_rated']] + cess_tag_ids
        for record in self:
            gstr_section = ''
            move_type = record.move_type
            l10n_in_gst_treatment = record.l10n_in_gst_treatment

            # Determine interstate and intra state conditions
            is_interstate = record.country_code == "IN" and record.l10n_in_state_id and record.l10n_in_state_id != record.company_id.state_id
            is_intrastate = record.country_code == "IN" and record.l10n_in_state_id and record.l10n_in_state_id == record.company_id.state_id

            # Detemine line tag and gst related conditions
            line_tags = record.invoice_line_ids.tax_tag_ids
            has_gst_tags = any(tag in gst_tags for tag in line_tags.ids)
            igst_amount = any('IGST' in tag.name for tag in line_tags)

            # Determine the treatment conditions
            is_unregistered_or_consumer = l10n_in_gst_treatment in ('unregistered', 'consumer')
            is_b2c_interstate = is_unregistered_or_consumer and is_interstate and (
                (record.reversed_entry_id and record.reversed_entry_id.amount_total > 250000) or
                (record.debit_origin_id and record.debit_origin_id.amount_total > 250000) or
                record.amount_total > 250000)
            is_regular_or_uin_holder_or_composition = l10n_in_gst_treatment in ("regular", "uin_holders", "composition")

            # Determine move type condition
            move_type_is_invoice_receipt_refund = move_type in ['out_invoice', 'out_receipt', 'out_refund']
            move_type_is_invoice_receipt_no_debit = move_type in ['out_invoice', 'out_receipt'] and not record.debit_origin_id and has_gst_tags
            move_type_is_refund_or_invoice_with_debit = (move_type == 'out_refund' or (move_type == 'out_invoice' and record.debit_origin_id)) and has_gst_tags

            # Conditions for determining l10n_in_gstr_section
            conditions = [
                (move_type_is_invoice_receipt_refund and (
                    (l10n_in_gst_treatment == 'overseas' and any(tag in export_tags for tag in line_tags.ids)) or
                    (l10n_in_gst_treatment in ('special_economic_zone', 'deemed_export') and any(tag_id == taxes_tag_ids['zero_rated'] for tag_id in line_tags.ids))),
                    'expwp' if igst_amount else 'expwop'),
                (move_type_is_invoice_receipt_refund and l10n_in_gst_treatment == 'special_economic_zone' and nil_and_gst_tags,
                    'sezwp' if igst_amount else 'sezwop'),
                (move_type_is_invoice_receipt_refund and l10n_in_gst_treatment == 'deemed_export' and has_gst_tags, 'de'),
                (move_type_is_invoice_receipt_no_debit and is_regular_or_uin_holder_or_composition,
                    'b2b_reverse_charge' if any(tax.l10n_in_reverse_charge for line in record.invoice_line_ids for tax in line.tax_ids) else 'b2b_regular'),
                (move_type_is_invoice_receipt_no_debit and is_b2c_interstate, 'b2cl'),
                (move_type_is_invoice_receipt_refund and is_unregistered_or_consumer and has_gst_tags and (
                    is_intrastate or (is_interstate and record.amount_total <= 250000)), 'b2cs'),
                (move_type_is_refund_or_invoice_with_debit and is_regular_or_uin_holder_or_composition, 'cdnr'),
                (move_type_is_refund_or_invoice_with_debit and is_b2c_interstate, 'cdnur'),
            ]

            # Evaluate conditions
            for condition, section in conditions:
                if condition:
                    gstr_section = section
                    break

            record.l10n_in_gstr_section = gstr_section

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

    @api.model
    def _get_l10n_in_taxes_tags_id_by_name(self, only_gst_tags=False):
        tags_name = ['sgst', 'cgst', 'igst', 'cess']
        if not only_gst_tags:
            tags_name += [f'base_{tax_name}' for tax_name in tags_name] + ['zero_rated', 'exempt', 'nil_rated', 'non_gst_supplies']
        return {
            tag_name: self.env['ir.model.data']._xmlid_to_res_id(f"l10n_in.tax_tag_{tag_name}")
            for tag_name in tags_name
        }

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
    def _l10n_in_extract_digits(self, string):
        if not string:
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

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
            move.write({'l10n_in_gstr_json': move.generate_json_data()})
        return posted

    def generate_json_data(self):
        tags_id = self._get_l10n_in_taxes_tags_id_by_name()
        hsn_tags = [tags_id[key] for key in ['exempt', 'nil_rated', 'non_gst_supplies', 'base_sgst', 'sgst', 'base_cgst', 'cgst', 'base_igst', 'igst', 'base_cess', 'cess']]
        for move in self:
            line_details = []
            tax_details_by_move = self._get_tax_details([('move_id', '=', move.id)])
            tax_details = tax_details_by_move.get(move, {})
            for line, line_tax_details in tax_details.items():
                if line.display_type != 'product' or not line.tax_ids:
                    continue
                base_line_tag_ids = line.tax_tag_ids.ids
                uqc = "NA"
                if line.product_id.type != 'service':
                    uqc = line.product_uom_id.l10n_in_code and line.product_uom_id.l10n_in_code.split("-")[0] or "OTH"
                lines_json = {
                    'hsn_sc': self._l10n_in_extract_digits(line.l10n_in_hsn_code),
                    'uqc': uqc,
                    'product_type': line.product_id.type,
                    'qty': line.quantity,
                    'zero_rated_type': False,
                    'include_in_hsn': False,
                    'base_amount': line_tax_details['base_amount'],
                    'l10n_in_reverse_charge': line_tax_details['l10n_in_reverse_charge'],
                    'gst_tax_rate': line_tax_details['gst_tax_rate'],
                    'igst': line_tax_details['igst'],
                    'cgst': line_tax_details['cgst'],
                    'sgst': line_tax_details['sgst'],
                    'cess': line_tax_details['cess'],
                    }
                if any(tag in hsn_tags for tag in base_line_tag_ids):
                    lines_json['include_in_hsn'] = True
                if tags_id['nil_rated'] in base_line_tag_ids:
                    lines_json['zero_rated_type'] = 'nil_rated'
                elif tags_id['exempt'] in base_line_tag_ids:
                    lines_json['zero_rated_type'] = 'exempt'
                elif tags_id['non_gst_supplies'] in base_line_tag_ids:
                    lines_json['zero_rated_type'] = 'non_gst_supplies'
                line_details.append(lines_json)

            return {
                'move_type': move.move_type,
                'line_details': line_details,
            }

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

    def _get_tax_details(self, domain):
        """
            return {
                account.move(1): {
                    account.move.line(1):{
                        'base_amount': 100,
                        'gst_tax_rate': 18.00,
                        'igst': 0.00,
                        'cgst': 9.00,
                        'sgst': 9.00,
                        'cess': 3.33,
                        'line_tax_details': {tax_details}
                    }
                }
            }
        """
        tax_vals_map = {}
        cgst_tag_ids = [self.env.ref("l10n_in.tax_tag_cgst").id, self.env.ref("l10n_in.tax_tag_base_cgst").id]
        sgst_tag_ids = [self.env.ref("l10n_in.tax_tag_sgst").id, self.env.ref("l10n_in.tax_tag_base_sgst").id]
        # Mapping of tax group names to their IDs
        tax_group_mapping = {
            group: self.env.ref(f'account.{self.company_id.root_id.id}_{group}_group').id
            for group in ['igst', 'cgst', 'sgst', 'cess']
        }
        journal_items = self.env['account.move.line'].search(domain)
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details_from_domain(domain=[('id', 'in', journal_items.ids)])
        self._cr.execute(tax_details_query, tax_details_params)
        tax_details = self._cr.dictfetchall()
        # Retrieve base lines and tax lines based on tax_details
        base_lines = self.env['account.move.line'].browse([tax['base_line_id'] for tax in tax_details])
        tax_lines = self.env['account.move.line'].browse([tax['tax_line_id'] for tax in tax_details])
        base_lines_map = {line.id: line for line in base_lines}
        tax_lines_map = {line.id: line for line in tax_lines}
        for tax_vals in tax_details:
            base_line = base_lines_map[tax_vals['base_line_id']]
            tax_line = tax_lines_map[tax_vals['tax_line_id']]
            journal_items -= base_line
            journal_items -= tax_line
            move_id = base_line.move_id
            tax_vals_map.setdefault(move_id, {}).setdefault(base_line, {
                'base_amount': tax_vals['base_amount'],
                'l10n_in_reverse_charge': tax_line.tax_line_id.l10n_in_reverse_charge,
                'gst_tax_rate': tax_line.group_tax_id.amount or tax_line.tax_line_id.amount,
                'igst': 0.00,
                'cgst': 0.00,
                'sgst': 0.00,
                'cess': 0.00,
                'line_tax_details': [],
            })
            tax_group = next((tax_group for tax_group, group_id in tax_group_mapping.items() if tax_line.tax_group_id.id == group_id), None)
            tax_vals['tax_type'] = tax_group.upper() if tax_group else None
            tax_vals_map[move_id][base_line]['line_tax_details'].append(tax_vals)
            if tax_group:
                tax_vals_map[move_id][base_line][tax_group] += tax_vals['tax_amount']
            # Calculate GST rate for each base line
            base_tags_ids = base_line.tax_tag_ids.ids
            if len(base_tags_ids) == 2 and any(tag in base_tags_ids for tag in cgst_tag_ids) and any(tag in base_tags_ids for tag in sgst_tag_ids):
                tax_vals_map[move_id][base_line]['gst_tax_rate'] = sum(base_line.tax_ids.mapped('amount'))

        # IF line have 0% tax or not have tax then we add it manually
        for journal_item in journal_items:
            move_id = journal_item.move_id
            tax_vals_map.setdefault(move_id, {}).setdefault(journal_item, {
                'base_amount': journal_item.balance,
                'l10n_in_reverse_charge': False,
                'gst_tax_rate': 0.0,
                'igst': 0.00,
                'cgst': 0.00,
                'sgst': 0.00,
                'cess': 0.00,
                'line_tax_details': [],
            })
        return tax_vals_map
