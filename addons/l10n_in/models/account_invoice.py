# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.tools.image import image_data_uri
from odoo.tools.date_utils import get_fiscal_year


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
        def check_aggregate_limits(totals):
            return [
                tax_group_id
                for tax_group_id, total in totals.items()
                if (tax_group_id.l10n_in_is_aggregate_limit
                    and total > tax_group_id.l10n_in_aggregate_limit
                    and move._l10n_in_is_warning_applicable(tax_group_id))
            ]

        def check_per_transection_limits(totals):
            return [
                tax_group_id
                for tax_group_id, limits in totals.items()
                for limit in limits
                if (
                    tax_group_id.l10n_in_is_per_transaction_limit
                    and limit > tax_group_id.l10n_in_per_transaction_limit
                    and move._l10n_in_is_warning_applicable(tax_group_id)
                )
            ]

        def filter_warning_sections(move, warning_sections):
            filtered_sections_tcs, filtered_sections_tds = set(), set()
            for line in move.invoice_line_ids:
                section = line.l10n_in_tds_tcs_section
                if (
                    section in warning_sections
                    and section not in line.tax_ids.mapped('tax_group_id')
                    and line._l10n_in_get_line_amount()
                    and (
                        (
                            section.l10n_in_per_transaction_units == 'per_unit'
                            and line._l10n_in_compute_price_total(is_aggregate=False) > section.l10n_in_per_transaction_limit
                        ) or section.l10n_in_per_transaction_units == 'total'
                    )
                ):
                    section_name = section.name[5:]
                    if section.l10n_in_tax_source_type == 'tcs':
                        filtered_sections_tcs.add(section_name)
                    elif section.l10n_in_tax_source_type == 'tds':
                        filtered_sections_tds.add(section_name)

            return filtered_sections_tcs, filtered_sections_tds

        for move in self:
            if move.country_code == 'IN' and move.state == 'posted':
                warning_sections = []
                per_transaction_total, per_transection_unit, aggregate_yearly, aggregate_monthly = move._get_l10n_in_tax_totals(move.partner_id)

                # per transaction limit check
                for tax_totals in [per_transaction_total, per_transection_unit]:
                    warning_sections.extend(check_per_transection_limits(tax_totals))

                # aggregate limit check
                for tax_totals in [aggregate_yearly, aggregate_monthly]:
                    warning_sections.extend(check_aggregate_limits(tax_totals))

                if move.move_type in ['out_invoice', 'in_invoice', 'entry']:
                    for line in move.invoice_line_ids:
                        line.l10n_in_line_warning = (
                            line.l10n_in_tds_tcs_section
                            and line.l10n_in_tds_tcs_section not in line.tax_ids.mapped('tax_group_id')
                            and line._l10n_in_get_line_amount()
                            and line._l10n_in_compute_tcs_tds_line_warning(warning_sections)
                        )

                warning_sections_tcs, warning_sections_tds = filter_warning_sections(move, warning_sections)

                warnings = []
                if (move.journal_id.type == 'sale' and move.move_type == 'out_invoice'):
                    warnings.append("collect TCS u/s %s" % ', '.join(warning_sections_tcs))
                elif (move.journal_id.type == 'purchase' and move.move_type == 'in_invoice'):
                    warnings.append("deduct TDS u/s %s" % ', '.join(warning_sections_tds))
                elif move.is_entry():
                    if warning_sections_tcs:
                        warnings.append("collect TCS u/s %s" % ', '.join(warning_sections_tcs))
                    if warning_sections_tds:
                        warnings.append("deduct TDS u/s %s" % ', '.join(warning_sections_tds))

                move.l10n_in_tcs_tds_warning = (
                    (warning_sections_tcs or warning_sections_tds) and
                    _("It's advisable to %s on this transaction.") % ' and '.join(warnings) or
                    False
                )

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

    def _l10n_in_get_parent_and_branch_compnies(self, company):
        company_ids = company
        if company.parent_id:
            company_ids |= company.parent_id
            if company.parent_id.child_ids:
                company_ids |= company.parent_id.mapped('child_ids')
        if company.child_ids:
            company_ids |= company.mapped('child_ids')
        return company_ids

    def _l10n_in_is_warning_applicable(self, tax_group_id):
        return (
            (tax_group_id.l10n_in_tax_source_type == 'tcs' and self.journal_id.type == 'sale')
            or (tax_group_id.l10n_in_tax_source_type == 'tds' and self.journal_id.type == 'purchase')
            or self.is_entry()
        )

    def _get_l10n_in_tax_totals(self, partners):
        self.ensure_one()
        company_ids = self._l10n_in_get_parent_and_branch_compnies(self.company_id)
        section_ids = self.invoice_line_ids.mapped('l10n_in_tds_tcs_section')
        start_date, end_date = get_fiscal_year(self.date, day=self.company_id.fiscalyear_last_day, month=int(self.company_id.fiscalyear_last_month))
        month_start_date = fields.Date.start_of(self.date, "month")
        month_end_date = fields.Date.end_of(self.date, "month")
        query = """
            WITH computed_lines AS (
                SELECT
                    aml.id AS line_id,
                    aml.quantity,
                    am.id AS move_id,
                    am.date,
                    am.state,
                    rp.id AS partner_id,
                    atg.id AS section_id,
                    atg.l10n_in_is_per_transaction_limit,
                    atg.l10n_in_is_aggregate_limit,
                    atg.l10n_in_tax_source_type,
                    atg.l10n_in_per_transaction_units,
                    atg.l10n_in_aggregate_period,
                    acc.l10n_in_tds_tcs_section AS section_code,
                    (am.move_type IN ('in_invoice', 'out_refund')) AS is_outbound,
                    (am.move_type IN ('out_invoice', 'in_refund')) AS is_inbound,
                    CASE
                        WHEN atg.l10n_in_consider_tax = 'total_amount' THEN (
                        CASE
                            WHEN aml.balance < 0 THEN -1
                            ELSE 1
                        END
                        ) * ((
                            SELECT SUM((tax.amount / 100) * ABS(aml.balance))
                            FROM account_tax tax
                            JOIN account_move_line_account_tax_rel aml_tax_rel ON aml_tax_rel.account_tax_id = tax.id
                            WHERE aml_tax_rel.account_move_line_id = aml.id
                        ) + ABS(aml.balance))
                        ELSE balance
                    END AS total_amount
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                JOIN account_account acc ON acc.id = aml.account_id
                JOIN account_tax_group atg ON atg.id = acc.l10n_in_tds_tcs_section
                JOIN res_partner rp ON rp.id = am.partner_id
                WHERE am.date >= %s
                    AND am.date <= %s
                    AND am.company_id IN %s
                    AND am.partner_id IN (
                        SELECT p2.id
                        FROM res_partner p1
                        JOIN res_partner p2 ON p1.l10n_in_pan = p2.l10n_in_pan
                        WHERE p1.id = %s
                    )
                    AND acc.l10n_in_tds_tcs_section IS NOT NULL
                    AND acc.l10n_in_tds_tcs_section IN %s
                    AND (am.state = 'posted' OR am.id = %s)
            ),
            computed_lines_for_per_transection AS (
                SELECT
                    section_id,
                    CASE
                        WHEN l10n_in_is_per_transaction_limit = TRUE AND l10n_in_per_transaction_units = 'per_unit'
                        THEN ARRAY_AGG(ABS(total_amount) / quantity)
                        ELSE ARRAY_AGG(0)
                    END AS per_transection_per_unit,
                    CASE
                        WHEN l10n_in_is_per_transaction_limit = TRUE AND l10n_in_per_transaction_units = 'total'
                        THEN SUM(ABS(total_amount))
                        ELSE 0
                    END AS per_transection_total
                FROM computed_lines
                WHERE move_id = %s
                GROUP BY section_id, l10n_in_is_per_transaction_limit, l10n_in_per_transaction_units
            ),
            computed_lines_for_aggregate AS (
                SELECT
                    cl.section_id,
                    SUM(
                        CASE
                            WHEN cl.l10n_in_is_aggregate_limit
                                AND (cl.is_inbound or cl.is_outbound)
                            THEN
                                CASE
                                    WHEN cl.l10n_in_tax_source_type = 'tds'
                                    THEN cl.total_amount
                                    ELSE -cl.total_amount
                                END
                            ELSE 0
                        END
                    ) AS tax_totals_aggregate
                FROM computed_lines cl
                GROUP BY cl.section_id
            ),
            computed_lines_for_aggregate_monthly AS (
                SELECT
                    cl.section_id,
                    SUM(
                        CASE
                            WHEN cl.l10n_in_is_aggregate_limit
                                AND (cl.is_inbound or cl.is_outbound)
                                AND cl.l10n_in_aggregate_period = 'month'
                            THEN
                                CASE
                                    WHEN cl.l10n_in_tax_source_type = 'tds'
                                    THEN cl.total_amount
                                    ELSE -cl.total_amount
                                END
                            ELSE 0
                        END
                    ) AS tax_totals_aggregate
                FROM computed_lines cl
                WHERE date >= %s
                    AND date <= %s
                GROUP BY cl.section_id
            )
            SELECT
                cla.section_id,
                clpt.per_transection_per_unit,
                clpt.per_transection_total,
                cla.tax_totals_aggregate,
                clam.tax_totals_aggregate
            FROM computed_lines_for_aggregate cla
            JOIN computed_lines_for_per_transection clpt ON clpt.section_id = cla.section_id
            JOIN computed_lines_for_aggregate_monthly clam ON clam.section_id = clam.section_id
            GROUP BY cla.section_id,
                clpt.per_transection_per_unit,
                clpt.per_transection_total,
                clam.tax_totals_aggregate,
                cla.tax_totals_aggregate
        """

        params = [start_date, end_date, tuple(company_ids.ids), tuple(partners.ids), tuple(section_ids.ids), self.id, self.id, month_start_date, month_end_date]
        self.env.cr.execute(query, params)
        result = self.env.cr.fetchall()

        aggregate_monthly = {}
        aggregate_yearly = {}
        tax_per_transection_unit_total = {}
        tax_per_transaction_total = {}
        for section_id, per_transection_unit, per_transaction_total, yearly_total, monthly_total in result:
            section = self.env['account.tax.group'].browse(section_id)
            if section.l10n_in_aggregate_period == 'month':
                aggregate_monthly[section] = monthly_total or 0
            else:
                aggregate_yearly[section] = yearly_total or 0
            if section.l10n_in_per_transaction_units == 'per_unit':
                tax_per_transection_unit_total[section] = per_transection_unit or 0
            else:
                tax_per_transaction_total[section] = [per_transaction_total or 0]

        return tax_per_transaction_total, tax_per_transection_unit_total, aggregate_yearly, aggregate_monthly

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
