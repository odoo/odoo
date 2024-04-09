# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.tools.image import image_data_uri
from odoo.addons.l10n_in.const import TCS_GROUPS, TDS_GROUPS


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
    l10n_in_tcs_tds_warning = fields.Char('TDC/TCS Warning', compute="_compute_l10n_in_tcs_tds_warning", store=True)

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

    @api.depends('state')
    def _compute_l10n_in_tcs_tds_warning(self):
        def compute_warning_sections(move):
            def check_per_transaction_limits(per_transaction_total):
                sections = []
                for tax_group_id, limits in per_transaction_total.items():
                    for limit in limits:
                        if (
                            tax_group_id.l10n_in_is_per_transaction_limit
                            and limit > tax_group_id.l10n_in_per_transaction_limit
                            and tax_group_id.name[5:] not in sections
                            and is_warning_applicable(tax_group_id)
                        ):
                            sections.append(tax_group_id.name[5:])
                return sections

            def check_aggregate_limits(totals):
                sections = []
                for partner, tax_group_ids in totals.items():
                    for tax_group_id, total in tax_group_ids.items():
                        if (
                            tax_group_id.l10n_in_is_aggregate_limit
                            and total > tax_group_id.l10n_in_aggregate_limit
                            and move.invoice_line_ids.filtered(lambda l: l.account_id.l10n_in_tds_tcs_section not in l.tax_ids.mapped('tax_group_id') and (l.price_unit != 0 or (l.move_id.move_type == 'entry' and (l.credit != 0 or l.debit != 0))))
                            and tax_group_id.name[5:] not in sections
                            and is_warning_applicable(tax_group_id)
                        ):
                            sections.append(tax_group_id.name[5:])
                return sections

            def is_warning_applicable(tax_group_id):
                tax_group_xml_id = move._get_tax_group_xml_id(tax_group_id)
                return (
                    (tax_group_xml_id in TCS_GROUPS and move.journal_id.type == 'sale')
                    or (tax_group_xml_id in TDS_GROUPS and move.journal_id.type == 'purchase')
                    or (
                        tax_group_xml_id in TCS_GROUPS
                        and move.move_type == 'entry'
                        and move.line_ids.filtered(lambda l: l.account_id.l10n_in_tds_tcs_section and move._get_tax_group_xml_id(l.account_id.l10n_in_tds_tcs_section) in TCS_GROUPS and l.debit == 0)
                    )
                    or (
                        tax_group_xml_id in TDS_GROUPS
                        and move.move_type == 'entry'
                        and move.line_ids.filtered(lambda l: l.account_id.l10n_in_tds_tcs_section and move._get_tax_group_xml_id(l.account_id.l10n_in_tds_tcs_section) in TDS_GROUPS and l.credit == 0)
                    )
                )

            def check_line_warnings(move, warning_sections):
                for line in move.invoice_line_ids:
                    tax_group = line.account_id.l10n_in_tds_tcs_section
                    section_name = tax_group and tax_group.name[5:]
                    line_price = line.price_unit if line.move_id.move_type != 'entry' else (line.credit or line.debit)
                    if is_line_warning_applicable(line, tax_group):
                        set_line_warning(line, tax_group, line_price, warning_sections, section_name)
                    else:
                        line.l10n_in_line_warning = False

            def is_line_warning_applicable(line, tax_group):
                return (
                    (line.move_id.journal_id.type == 'sale' and line.move_id.move_type == 'out_invoice')
                    or (line.move_id.journal_id.type == 'purchase' and line.move_id.move_type == 'in_invoice')
                    or (line.move_id.move_type == 'entry')
                ) and tax_group and tax_group not in line.tax_ids.mapped('tax_group_id') and (line.price_unit != 0 or (line.move_id.move_type == 'entry' and (line.credit != 0 or line.debit != 0)))

            def set_line_warning(line, tax_group, line_price, warning_sections, section_name):
                if section_name not in warning_sections:
                    if tax_group.l10n_in_per_transection_units == 'per_unit':
                        line.l10n_in_line_warning = tax_group.l10n_in_is_per_transaction_limit and line_price > tax_group.l10n_in_per_transaction_limit and is_warning_applicable(tax_group)
                    else:
                        if any(tax_group in l.account_id.l10n_in_tds_tcs_section and (l.price_unit != 0 or (l.move_id.move_type == 'entry' and (l.credit != 0 or l.debit != 0))) for l in line.move_id.invoice_line_ids):
                            if line.move_id.invoice_line_ids.filtered(lambda l: tax_group in l.tax_ids.mapped('tax_group_id')):
                                line.l10n_in_line_warning = is_warning_applicable(tax_group)
                                warning_sections.append(section_name)
                            else:
                                line.l10n_in_line_warning = False
                        else:
                            line.l10n_in_line_warning = False
                else:
                    if tax_group.l10n_in_per_transection_units == 'per_unit':
                        if (
                            tax_group.l10n_in_is_per_transaction_limit and line_price > tax_group.l10n_in_per_transaction_limit
                            and is_warning_applicable(tax_group)
                        ):
                            line.l10n_in_line_warning = True
                        else:
                            line.l10n_in_line_warning = False
                    else:
                        if line.move_id.move_type == 'entry' and tax_group.l10n_in_is_per_transaction_limit:
                            if line_price > tax_group.l10n_in_per_transaction_limit:
                                line.l10n_in_line_warning = True
                            else:
                                line.l10n_in_line_warning = is_warning_applicable(tax_group)
                        else:
                            line.l10n_in_line_warning = is_warning_applicable(tax_group)

            warning_sections = []
            per_transaction_total = move._l10n_in_calculate_per_transaction_total()
            tax_fiscal_yearly_totals, tax_monthly_totals = move._l10n_in_calculate_aggregate_totals(
                move.invoice_line_ids.mapped('partner_id')
            )

            warning_sections.extend(check_per_transaction_limits(per_transaction_total))
            warning_sections.extend(check_aggregate_limits(tax_fiscal_yearly_totals))
            warning_sections.extend(check_aggregate_limits(tax_monthly_totals))

            check_line_warnings(move, warning_sections)
            return warning_sections

        def filter_warning_sections(move, warning_sections):
            filtered_sections = []
            for section in warning_sections:
                lines = move.invoice_line_ids.filtered(lambda line: line.account_id.l10n_in_tds_tcs_section and section == line.account_id.l10n_in_tds_tcs_section.name[5:])
                if lines.filtered(lambda l: l.account_id.l10n_in_tds_tcs_section not in l.tax_ids.mapped('tax_group_id')):
                    if section not in filtered_sections:
                        filtered_sections.append(section)
            return filtered_sections

        def generate_warning_message(move, warning_sections):
            warning = ', '.join(warning_sections)
            if (move.journal_id.type == 'sale' and move.move_type == 'out_invoice') and move.move_type == 'entry':
                return len(warning_sections) > 0 and _("It's advisable to collect TCS u/s %s on this transaction.", warning) or False
            elif (move.journal_id.type == 'purchase' and move.move_type == 'in_invoice') or move.move_type == 'entry':
                return len(warning_sections) > 0 and _("It's advisable to deduct TDS u/s %s on this transaction.", warning) or False
            return False

        for move in self:
            if move.country_code == 'IN' and move.state == 'posted':
                warning_sections = compute_warning_sections(move)
                warning_sections = filter_warning_sections(move, warning_sections)
                move.l10n_in_tcs_tds_warning = generate_warning_message(move, warning_sections)

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

    def _l10n_in_calculate_aggregate_totals(self, partner_id):
        def get_company_ids(company):
            company_ids = company
            if company.parent_id:
                company_ids |= company.parent_id
                if company.parent_id.child_ids:
                    company_ids |= company.parent_id.mapped('child_ids')
            if company.child_ids:
                company_ids |= company.mapped('child_ids')
            return company_ids

        def get_partner_ids(partner_domain):
            return self.env['res.partner'].search(partner_domain)

        def get_move_lines(partner_domain, start_date, end_date, account_ids, period):
            company_ids = get_company_ids(self.company_id)
            partner_ids = get_partner_ids(partner_domain)
            query = """
                SELECT line.id
                FROM account_move_line line
                JOIN account_move move ON line.move_id = move.id
                JOIN account_account account ON line.account_id = account.id
                WHERE move.date >= %s
                    AND move.date <= %s
                    AND move.company_id IN %s
                    AND account.id IN %s
                    AND account.l10n_in_tds_tcs_section IS NOT NULL
                    AND account.l10n_in_tds_tcs_section IN (
                        SELECT id
                        FROM account_tax_group
                        WHERE l10n_in_aggregate_period = %s
                    )
            """
            if partner_ids:
                partner_condition = "AND line.partner_id IN %s"
                query += f"\n{partner_condition}"
                params = (start_date, end_date, tuple(company_ids.ids), tuple(account_ids.ids), period, tuple(partner_ids.ids))
            else:
                params = (start_date, end_date, tuple(company_ids.ids), tuple(account_ids.ids), period)
            self.env.cr.execute(query, params)
            line_ids = [row[0] for row in self.env.cr.fetchall()]
            invoice_lines = self.env['account.move.line'].browse(line_ids)

            lines_group_by_partners = {}
            for line in invoice_lines:
                partner_pan = line.partner_id.l10n_in_pan or line.partner_id.id
                if partner_pan not in lines_group_by_partners:
                    lines_group_by_partners[partner_pan] = line
                lines_group_by_partners[partner_pan] |= line
            return lines_group_by_partners

        def calculate_fiscal_year_dates():
            fiscal_year_end_date = fields.Date.from_string('%s-%s-%s' % (fields.Date.today().year + 1, self.company_id.fiscalyear_last_month, self.company_id.fiscalyear_last_day))
            fiscal_year_start_date = fields.Date.add(fields.Date.subtract(fiscal_year_end_date, months=12), days=1)
            return fiscal_year_start_date, fiscal_year_end_date

        def get_partner_domain():
            if not partner_id:
                return []

            if partner_id.filtered(lambda p: p.l10n_in_pan):
                return ['|', ('l10n_in_pan', 'in', partner_id.mapped('l10n_in_pan')), ('id', 'in', partner_id.ids)]
            else:
                return [('id', 'in', partner_id.ids)]

        fiscal_year_start_date, fiscal_year_end_date = calculate_fiscal_year_dates()
        partner_domain = get_partner_domain()
        account_ids = self.invoice_line_ids.mapped('account_id')

        moves_within_fiscal_year = get_move_lines(
            partner_domain=partner_domain,
            start_date=fiscal_year_start_date,
            end_date=fiscal_year_end_date,
            account_ids=account_ids,
            period='fiscal_year'
        )
        tax_fiscal_yearly_totals = self._l10n_in_calculate_tax_aggregate_totals(moves_within_fiscal_year)

        tax_monthly_totals = {}
        if self.invoice_line_ids.filtered(lambda line: line.account_id.l10n_in_tds_tcs_section.l10n_in_aggregate_period == 'month'):
            month_start_date = fields.Date.start_of(self.date, "month")
            month_end_date = fields.Date.end_of(self.date, "month")
            moves_within_month = get_move_lines(
                partner_domain=partner_domain,
                start_date=month_start_date,
                end_date=month_end_date,
                account_ids=account_ids,
                period='month'
            )
            tax_monthly_totals = self._l10n_in_calculate_tax_aggregate_totals(moves_within_month)

        return tax_fiscal_yearly_totals, tax_monthly_totals

    def _l10n_in_calculate_tax_aggregate_totals(self, records):
        all_tax_totals = {}
        for partner in records:
            accounts = records[partner].mapped('account_id')
            if (tax_totals := {
                account.l10n_in_tds_tcs_section: 0 for account in accounts.filtered(
                    lambda account: account.l10n_in_tds_tcs_section
                )
            }):
                for line in records[partner]:
                    tax_group_id = line.account_id.l10n_in_tds_tcs_section
                    if tax_group_id.l10n_in_is_aggregate_limit:
                        xml_id = self._get_tax_group_xml_id(tax_group_id)

                        if line.tax_ids and line.move_id.move_type == 'entry':
                            line_price = line.debit if line.credit == 0 else line.credit
                            taxes_res = line.tax_ids.compute_all(line_price)
                            line.price_total = taxes_res['total_included']

                        if xml_id in TDS_GROUPS:
                            if line.move_id.move_type in ['out_refund', 'in_invoice']:
                                tax_totals[tax_group_id] += line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.price_subtotal
                            elif line.move_id.move_type in ['out_invoice', 'in_refund']:
                                tax_totals[tax_group_id] -= line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.price_subtotal
                            elif line.move_id.move_type == 'entry':
                                if line.credit == 0:
                                    tax_totals[tax_group_id] += line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.debit
                                else:
                                    tax_totals[tax_group_id] -= line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.credit
                        else:
                            if line.move_id.move_type in ['out_invoice', 'in_refund']:
                                tax_totals[tax_group_id] += line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.price_subtotal
                            elif line.move_id.move_type in ['out_refund', 'in_invoice']:
                                tax_totals[tax_group_id] -= line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.price_subtotal
                            elif line.move_id.move_type == 'entry':
                                if line.debit == 0:
                                    tax_totals[tax_group_id] += line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.credit
                                else:
                                    tax_totals[tax_group_id] -= line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.debit
                if partner not in all_tax_totals:
                    all_tax_totals[partner] = tax_totals

        return all_tax_totals

    def _l10n_in_calculate_per_transaction_total(self):
        def get_unit_value(line, tax_group_id):
            if line.move_id.move_type == 'entry':
                return get_entry_move_value(line, tax_group_id)
            else:
                return (line.price_total / line.quantity) if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.price_unit

        def get_total_value(line, tax_group_id):
            if line.move_id.move_type == 'entry':
                return get_entry_move_value(line, tax_group_id)
            else:
                return line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.price_subtotal

        def get_entry_move_value(line, tax_group_id):
            if line.credit == 0:
                return line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.debit
            else:
                return line.price_total if tax_group_id.l10n_in_consider_tax == 'total_amount' else line.credit

        self.ensure_one()
        per_transaction_total = {}

        for line in self.invoice_line_ids.filtered(lambda line: line.account_id.l10n_in_tds_tcs_section not in line.tax_ids.mapped('tax_group_id')):
            tax_group_id = line.account_id.l10n_in_tds_tcs_section
            if tax_group_id.l10n_in_is_per_transaction_limit:
                if line.tax_ids and line.move_id.move_type == 'entry':
                    line_price = line.debit if line.credit == 0 else line.credit
                    taxes_res = line.tax_ids.compute_all(line_price)
                    line.price_total = taxes_res['total_included']

                if tax_group_id.l10n_in_per_transection_units == 'per_unit':
                    unit_value = get_unit_value(line, tax_group_id)
                else:
                    unit_value = get_total_value(line, tax_group_id)

                if line.move_id.move_type != 'entry':
                    if tax_group_id not in per_transaction_total:
                        per_transaction_total[tax_group_id] = [unit_value]
                    elif tax_group_id.l10n_in_per_transection_units == 'total':
                        per_transaction_total[tax_group_id][0] += unit_value
                    elif tax_group_id.l10n_in_per_transection_units == 'per_unit':
                        per_transaction_total[tax_group_id].append(unit_value)
                else:
                    if tax_group_id not in per_transaction_total:
                        per_transaction_total[tax_group_id] = [unit_value]
                    else:
                        per_transaction_total[tax_group_id].append(unit_value)
        return per_transaction_total

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.country_code == 'IN':
            return 'l10n_in.l10n_in_report_invoice_document_inherit'
        return super()._get_name_invoice_report()

    def _get_tax_group_xml_id(self, tax_group_id):
        xml_id = self.env['ir.model.data'].search([('res_id', '=', tax_group_id.id), ('model', '=', 'account.tax.group')], limit=1)
        return xml_id.name[len(str(self.company_id.parent_id.id or self.company_id.id)) + 1:]

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
