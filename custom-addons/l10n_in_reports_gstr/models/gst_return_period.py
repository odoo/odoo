# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from babel.dates import get_quarter_names
from datetime import datetime, timedelta
from dateutil import relativedelta
from itertools import groupby
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.addons.iap import jsonrpc
from odoo.exceptions import UserError, AccessError, ValidationError, RedirectWarning
from odoo.tools import date_utils, get_lang, html_escape
from odoo.tools.misc import format_date
from odoo.addons.l10n_in_edi.models.account_edi_format import DEFAULT_IAP_ENDPOINT, DEFAULT_IAP_TEST_ENDPOINT

import logging

_logger = logging.getLogger(__name__)


class L10nInGSTReturnPeriod(models.Model):
    _name = "l10n_in.gst.return.period"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "GST Return Period"

    def _default_year(self):
        today_date = fields.Date.context_today(self)
        company = self.env.company
        if company.account_tax_periodicity == 'trimester':
            this_quarter = date_utils.get_quarter(today_date)
            if this_quarter and this_quarter[0].month == today_date.month and today_date.day <= 10:
                return (fields.Date.context_today(self) - relativedelta.relativedelta(months=3)).strftime('%Y')

        if today_date.day <= 10 and company.account_tax_periodicity == 'monthly':
            return (fields.Date.context_today(self) - relativedelta.relativedelta(months=1)).strftime('%Y')
        return today_date.strftime('%Y')

    def _default_month(self):
        today_date = default_date = fields.Date.context_today(self)
        if today_date.day <= 10:
            default_date = fields.Date.context_today(self) - relativedelta.relativedelta(months=1)
        return default_date.strftime('%m')

    def _default_quarterly(self):
        today_date = fields.Date.context_today(self)
        this_quarter = date_utils.get_quarter(today_date)
        default_date = this_quarter[0]
        if this_quarter and this_quarter[0].month == today_date.month and today_date.day <= 10:
            default_date = fields.Date.context_today(self) - relativedelta.relativedelta(months=3)
        return default_date.strftime('%m')


    name = fields.Char(compute="_compute_name", string="Period")
    return_period_month_year = fields.Char(compute="_compute_rtn_period_month_year", string="Return Period", store=True)
    tax_unit_id = fields.Many2one("account.tax.unit", string="GST Units")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company, required=True)
    company_ids = fields.Many2many(related="tax_unit_id.company_ids", string="Companies")
    start_date = fields.Date("Start Date", compute="_compute_period_dates", store=True)
    end_date = fields.Date("End Date", compute="_compute_period_dates", store=True)
    periodicity = fields.Selection([("monthly", "Monthly"), ("trimester", "Quarterly")], compute='_compute_periodicity', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id")
    month = fields.Selection([
        ("01", "January"),
        ("02", "February"),
        ("03", "March"),
        ("04", "April"),
        ("05", "May"),
        ("06", "June"),
        ("07", "July"),
        ("08", "August"),
        ("09", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December"),
        ], default=_default_month)
    quarter = fields.Selection([
        ("01", "January"),
        ("04", "April"),
        ("07", "July"),
        ("10", "October"),
        ], default=_default_quarterly)
    year = fields.Char(default=_default_year)
    invoice_amount = fields.Float(string='Customer Invoices', compute="_compute_invoice_total_amount")
    bill_amount = fields.Float(string='Vendor Bills', compute="_compute_bill_total_amount")
    expected_amount = fields.Float(string='Expected Amount', compute="_compute_expected_amount")

    # ===============================
    # GSTR-1
    # ===============================

    gstr_reference = fields.Char(string="GSTR-1 Submit Reference")
    gstr1_status = fields.Selection(selection=[
        ('to_send', 'To Send'),
        ('sending', 'Sending'),
        ('waiting_for_status', "Waiting for Status"),
        ('error_in_invoice', 'Error in Invoice'),
        ('sent', 'Sent'),
        ('filed', 'Filed'),
    ], default="to_send", readonly=True, tracking=True)
    gstr1_base_value = fields.Monetary("GSTR-1 Base Value")
    gstr1_error = fields.Html("Error of GSTR-1")
    gstr1_blocking_level = fields.Selection(
        selection=[('warning', 'Warning'), ('error', 'Error')],
        help="Blocks the current operation of the document depending on the error severity:\n"
        "  * Warning: there is an error that doesn't prevent the current Electronic Return filing operation to succeed.\n"
        "  * Error: there is an error that blocks the current Electronic Return filing operation.")

    # ===============================
    # GSTR-2B
    # ===============================

    gstr2b_status = fields.Selection(selection=[
        ('not_recived', 'Not Recived'),
        ('waiting_reception', 'Waiting Reception'),
        ('being_processed', 'Being Processed'),
        ('partially_matched', 'Partially Matched'),
        ('fully_matched', 'Matched'),
    ], default="not_recived", string="Status", readonly=True, tracking=True)
    # if there is big data then it's give in multi-json
    gstr2b_json_from_portal_ids = fields.Many2many('ir.attachment', string='GSTR2B JSON from portal')
    gstr2b_base_value = fields.Monetary("GSTR-2B Base Value")
    gstr2b_error = fields.Html("Error of GSTR-2B")
    gstr2b_blocking_level = fields.Selection(
        selection=[('warning', 'Warning'), ('error', 'Error')],
        help="Blocks the current operation of the document depending on the error severity:\n"
        "  * Warning: there is an error that doesn't prevent the current Electronic Return filing operation to succeed.\n"
        "  * Error: there is an error that blocks the current Electronic Return filing operation.")

    # ===============================
    # GSTR-3B
    # ===============================

    gstr3b_closing_entry = fields.Many2one('account.move', compute="_compute_gstr3b_closing_entry", store=True)
    gstr3b_status = fields.Selection(string="GSTR-3B Status", selection=[
        ('not_filed', 'Not Filed'),
        ('filed', 'Filed'),
    ], compute="_compute_gstr3b_status", store=True)

    # ===============================
    # GSTR Common Methods
    # ===============================

    _sql_constraints = [(
        'unique_period',
        'UNIQUE(company_id, month, year, quarter)',
        "Return period must be unique."
    )]

    @api.constrains('tax_unit_id')
    def _check_tax_unit(self):
        for record in self:
            if record.tax_unit_id and record.tax_unit_id.main_company_id != record.company_id:
                raise ValidationError(_('GST Unit main company is different than this period company.'))

    @api.constrains('month', 'quarter', 'year')
    def _check_gstr_status(self):
        for record in self:
            if record.gstr1_status != 'to_send' or record.gstr2b_status != 'not_recived':
                raise UserError("You cannot change GST filing period after sending/receiving GSTR data")

    @api.onchange('year')
    def _check_isyear(self):
        if self.year and len(self.year) != 4 or not self.year.isnumeric():
            raise UserError((f"The value [{self.year}] should be year"))

    @api.onchange('tax_unit_id')
    def on_chnage_tax_unit_id(self):
        if self.tax_unit_id:
            self.company_id = self.tax_unit_id.main_company_id

    def _compute_name(self):
        for period in self:
            if period.periodicity == "monthly":
                period.name = format_date(self.env, period.start_date, date_format="MMM-yyyy")
            elif period.periodicity == "trimester":
                quarter_names = get_quarter_names("abbreviated", locale=get_lang(self.env).code)
                period.name = quarter_names[date_utils.get_quarter_number(period.end_date)]
                period.name += format_date(self.env, period.start_date, date_format="-yyyy")
            else:
                period.name = False

    @api.depends("company_id")
    def _compute_periodicity(self):
        for record in self:
            periodicity = record.tax_unit_id.main_company_id.account_tax_periodicity or record.company_id.account_tax_periodicity
            if periodicity not in ["monthly", "trimester"]:
                raise UserError(("To Create Return Period Periodicity should be Monthly or Quarterly"))
            record.periodicity = periodicity

    @api.depends("company_ids", "company_id")
    def _compute_invoice_total_amount(self):
        AccountMove = self.env['account.move']
        for record in self:
            domain = [
                ('company_id', 'in', (record.company_ids or record.company_id).ids),
                ('move_type', 'in', AccountMove.get_sale_types(True)),
                ("invoice_date", ">=", record.start_date),
                ("invoice_date", "<=", record.end_date),
                ("state", "=", "posted"),
            ]
            total_by_companies = AccountMove._read_group(domain, [], ['amount_total_signed:sum'])
            record.invoice_amount = total_by_companies[0][0]

    @api.depends("company_ids", "company_id")
    def _compute_expected_amount(self):
        all_gst_tag = (
            self.env.ref("l10n_in.tax_tag_igst") +
            self.env.ref("l10n_in.tax_tag_cgst") +
            self.env.ref("l10n_in.tax_tag_sgst") +
            self.env.ref("l10n_in.tax_tag_cess")
        )
        for record in self:
            domain = [
                ('company_id', 'in', (record.company_ids + record.company_id).ids),
                ('move_id.move_type', 'in', self.env['account.move'].get_invoice_types(True)),
                ("date", ">=", record.start_date),
                ("date", "<=", record.end_date),
                ("move_id.state", "=", "posted"),
                ("tax_tag_ids", "in", all_gst_tag.ids),
            ]
            total_by_companies = self.env['account.move.line']._read_group(domain, ['company_id'], ['balance:sum'])
            total = 0.00
            for total_by_company in total_by_companies:
                if total_by_company[0].id in (record.company_ids or record.company_id).ids:
                    total += total_by_company[1] * -1
            record.expected_amount = total

    @api.depends("company_ids", "company_id")
    def _compute_bill_total_amount(self):
        AccountMove = self.env['account.move']
        for record in self:
            domain = [
                ('company_id', 'in', (record.company_ids + record.company_id).ids),
                ('move_type', 'in', AccountMove.get_purchase_types(True)),
                ("invoice_date", ">=", record.start_date),
                ("invoice_date", "<=", record.end_date),
                ("state", "=", "posted")
            ]
            total_by_companies = AccountMove._read_group(domain, ['company_id'], ['amount_total_signed:sum'])
            total = 0.00
            for total_by_company in total_by_companies:
                if total_by_company[0].id in (record.company_ids or record.company_id).ids:
                    total += total_by_company[1] * -1
            record.bill_amount = total

    @api.depends('month', 'quarter', 'year')
    def _compute_period_dates(self):
        for record in self:
            if record.periodicity == "monthly":
                period_start = fields.Date.context_today(self).replace(day=1, month=int(record.month), year=int(record.year))
                this_month_start, this_month_end = date_utils.get_month(period_start)
                record.start_date = this_month_start
                record.end_date = this_month_end
            else:
                period_start = fields.Date.context_today(self).replace(day=1, month=int(record.quarter), year=int(record.year))
                this_quarter_start, this_quarter_end = date_utils.get_quarter(period_start)
                record.start_date = this_quarter_start
                record.end_date = this_quarter_end

    @api.depends("start_date")
    def _compute_rtn_period_month_year(self):
        for period in self:
            if period.start_date:
                period.return_period_month_year = period.start_date.strftime("%m%Y")
            else:
                period.return_period_month_year = False

    @api.depends('end_date', 'company_id')
    def _compute_gstr3b_closing_entry(self):
        for return_period in self:
            closing_journal_entry = self.env['account.move'].search([
                ('tax_closing_end_date', '=', return_period.end_date),
                ('move_type', '=', 'entry'),
                ('company_id', '=', return_period.company_id.id)
            ], limit=1)
            return_period.gstr3b_closing_entry = closing_journal_entry
            return_period.gstr3b_status = closing_journal_entry.state == 'posted' and 'filed' or 'not_filed'

    @api.depends('gstr3b_closing_entry', 'gstr3b_closing_entry.state')
    def _compute_gstr3b_status(self):
        for return_period in self:
            return_period.gstr3b_status = return_period.gstr3b_closing_entry.state == 'posted' and 'filed' or 'not_filed'

    def _check_config(self):
        company = self.company_id
        action = self.env.ref('account.action_account_config')
        msg = ""
        if not company.vat:
            raise UserError(_("Please set company GSTIN"))
        if not company.sudo().l10n_in_gstr_gst_username:
            msg = _("First setup GST user name and validate using OTP from configuration")
        if not company._is_l10n_in_gstr_token_valid():
            msg = _("The NIC portal connection has expired. To re-initiate the connection, you can send an OTP request From configuration.")
        if msg:
            raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

    @api.ondelete(at_uninstall=False)
    def _restrict_delete_on_gstr_status(self):
        if self._context.get('force_delete'):
            _logger.info(
                'Force deleted GST Return Period %s by %s (%s)',
                self.ids,
                self.env.user.name,
                self.env.user.id
            )
        else:
            for record in self:
                if record.gstr1_status != 'to_send' or record.gstr2b_status != 'not_recived':
                    raise UserError("You cannot delete GST Return Period after sending/receiving GSTR data")

    def open_invoice_action(self):
        domain = [
            ('company_id', 'in', (self.company_ids + self.company_id).ids),
            ('move_type', 'in', self.env['account.move'].get_sale_types(True)),
            ("invoice_date", ">=", self.start_date),
            ("invoice_date", "<=", self.end_date),
            ("state", "=", "posted"),
        ]
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action['domain'] = domain
        return action

    def open_vendor_bill_action(self):
        domain = [
            ('company_id', 'in', (self.company_ids + self.company_id).ids),
            ('move_type', 'in', self.env['account.move'].get_purchase_types(True)),
            ("invoice_date", ">=", self.start_date),
            ("invoice_date", "<=", self.end_date),
            ("state", "=", "posted")
        ]
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action['domain'] = domain
        return action

    def open_expected_action(self):
        all_gst_tag = (
            self.env.ref("l10n_in.tax_tag_igst") +
            self.env.ref("l10n_in.tax_tag_cgst") +
            self.env.ref("l10n_in.tax_tag_sgst") +
            self.env.ref("l10n_in.tax_tag_cess")
        )
        domain = [
            ('company_id', 'in', (self.company_ids + self.company_id).ids),
            ('move_id.move_type', 'in', self.env['account.move'].get_invoice_types(True)),
            ("date", ">=", self.start_date),
            ("date", "<=", self.end_date),
            ("move_id.state", "=", "posted"),
            ("tax_tag_ids", "in", all_gst_tag.ids),
        ]
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all')
        action['domain'] = domain
        return action

    def _cron_refresh_gst_token(self):
        # If Token is already expired than we can't refresh it.
        companies = self.env['res.company'].search([('vat', '!=', False),
            ('partner_id.country_id.code', '=', 'IN'),
            ('l10n_in_gstr_gst_username', '!=', False),
            ("l10n_in_gstr_gst_auto_refresh_token", "=", True)])
        for company in companies:
            # If token is just refresh in last 30 min then no need to refresh it again
            if company._is_l10n_in_gstr_token_valid() and (
                company.l10n_in_gstr_gst_token_validity - fields.Datetime.now()) > timedelta(minutes=30):
                response = self._refresh_token_request(company)
                if response.get('error'):
                    message = ''.join([
                        f"<p><b>[{error.get('code', '')}]</b> - <b>{error.get('message', '')}</b></p>"
                        for error in response.get("error", {})])
                    _logger.warning(_('%s', message))
                    continue
                company.write({
                    "l10n_in_gstr_gst_token": response.get('txn'),
                    "l10n_in_gstr_gst_token_validity": fields.Datetime.now() + timedelta(hours=6)
                })

    def open_gst_return_period_form_view(self):
        self.ensure_one()
        return {
            "name": _("GST Return Period"),
            "res_model": "l10n_in.gst.return.period",
            "view_mode": "form",
            "res_id": self.id,
            "type": "ir.actions.act_window",
            "views": [[self.env.ref('l10n_in_reports_gstr.l10n_in_gst_return_period_form_view').id, "form"]],
        }

    def _get_error_lavel(self, error_codes):
        blocking_level = "error"
        if "RTN_24" in error_codes:
            # File Generation is in progress, please try after sometime.
            blocking_level = "warning"
        if "404" in error_codes:
            blocking_level = "warning"
        return blocking_level

    # ===============================
    # GSTR-1
    # ===============================

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
        igst_tag_id = self.env.ref("l10n_in.tax_tag_igst").id
        cgst_tag_id = self.env.ref("l10n_in.tax_tag_cgst").id
        sgst_tag_id = self.env.ref("l10n_in.tax_tag_sgst").id
        cess_tag_id = self.env.ref("l10n_in.tax_tag_cess").id
        all_gst_tag = (igst_tag_id, cgst_tag_id, sgst_tag_id)
        journal_items_ids = set(self.env['account.move.line'].with_context(prefetch_fields=False).search(domain).ids)
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details_from_domain(domain=domain)
        self._cr.execute(f'''
             WITH RECURSIVE tax_child_tree(id, child_ids) AS (
                SELECT tax_fil_rel.parent_tax,
                       ARRAY_AGG(tax_fil_rel.child_tax)
                  FROM account_tax_filiation_rel tax_fil_rel
              GROUP BY tax_fil_rel.parent_tax
             UNION ALL
                SELECT tax_fil_rel.parent_tax, ARRAY_APPEND(ct.child_ids, tax_fil_rel.parent_tax)
                  FROM account_tax_filiation_rel tax_fil_rel
                  JOIN tax_child_tree ct ON ct.id = tax_fil_rel.child_tax
            ),
            base_line_with_gst_rate AS (
                SELECT aml.id, sum(CASE WHEN at.amount_type != 'group' THEN at.amount ELSE 0 END) as gst_rate
                FROM account_move_line aml
                JOIN account_move_line_account_tax_rel aml_taxs ON aml_taxs.account_move_line_id = aml.id
                LEFT JOIN tax_child_tree tax_child ON aml_taxs.account_tax_id = tax_child.id
                JOIN account_tax at ON at.id = aml_taxs.account_tax_id or at.id = any(tax_child.child_ids)
                WHERE EXISTS(SELECT 1
                    FROM account_tax_repartition_line at_rl
                    JOIN account_account_tag_account_tax_repartition_line_rel tax_tag ON tax_tag.account_tax_repartition_line_id = at_rl.id
                   where (at_rl.tax_id = at.id OR at_rl.tax_id = aml_taxs.account_tax_id)
                     and tax_tag.account_account_tag_id in {all_gst_tag}
                )
                GROUP BY aml.id
            ),
            tax_line_with_tags AS (
                SELECT aml.id, array_agg(aml_tag.account_account_tag_id) as tag_ids
                FROM account_move_line aml
                JOIN account_account_tag_account_move_line_rel aml_tag ON aml_tag.account_move_line_id = aml.id
                GROUP BY aml.id
            )
            SELECT
                COALESCE(aml_gst_rate.gst_rate, 0) as gst_tax_rate,
                aml_tags.tag_ids,
                at.l10n_in_reverse_charge,
                CASE
                    WHEN {igst_tag_id} = any(aml_tags.tag_ids) THEN 'IGST'
                    WHEN {cgst_tag_id} = any(aml_tags.tag_ids) THEN 'CGST'
                    WHEN {sgst_tag_id} = any(aml_tags.tag_ids) THEN 'SGST'
                    WHEN {cess_tag_id} = any(aml_tags.tag_ids) THEN 'CESS'
                END as tax_type,
                tax_detail.*
            FROM ({tax_details_query}) AS tax_detail
       LEFT JOIN account_tax at ON at.id = tax_detail.tax_id
       LEFT JOIN base_line_with_gst_rate aml_gst_rate ON aml_gst_rate.id = tax_detail.base_line_id
       LEFT JOIN tax_line_with_tags aml_tags ON aml_tags.id = tax_detail.tax_line_id
        ''', tax_details_params)
        tax_vals_list = self._cr.dictfetchall()
        base_lines = self.env['account.move.line'].browse(el['base_line_id'] for el in tax_vals_list)
        base_lines.fetch(['move_id'])
        for tax_vals in tax_vals_list:
            journal_items_ids -= {tax_vals.get('base_line_id')}
            journal_items_ids -= {tax_vals.get('tax_line_id')}
            base_line = base_lines.browse(tax_vals.get('base_line_id'))
            move_id = base_line.move_id
            tax_vals_map.setdefault(move_id, {})
            tax_vals_map[move_id].setdefault(base_line, {
                'base_amount': tax_vals['base_amount'],
                'l10n_in_reverse_charge': tax_vals['l10n_in_reverse_charge'],
                'gst_tax_rate': tax_vals['gst_tax_rate'],
                'igst': 0.00,
                'cgst': 0.00,
                'sgst': 0.00,
                'cess': 0.00,
                'line_tax_details': [],
            })
            tax_vals_map[move_id][base_line]['line_tax_details'].append(tax_vals)
            if tax_vals.get('tax_type') == 'IGST':
                tax_vals_map[move_id][base_line]['igst'] += (tax_vals['tax_amount'])
            elif tax_vals.get('tax_type') == 'CGST':
                tax_vals_map[move_id][base_line]['cgst'] += (tax_vals['tax_amount'])
            elif tax_vals.get('tax_type') == 'SGST':
                tax_vals_map[move_id][base_line]['sgst'] += (tax_vals['tax_amount'])
            elif tax_vals.get('tax_type') == 'CESS':
                tax_vals_map[move_id][base_line]['cess'] += (tax_vals['tax_amount'])
        # IF line have 0% tax or not have tax then we add it manually
        journal_items = self.env['account.move.line'].browse(list(journal_items_ids))
        journal_items.fetch(['move_id', 'balance'])
        for journal_item in journal_items:
            move_id = journal_item.move_id
            tax_vals_map.setdefault(move_id, {})
            tax_vals_map[move_id].setdefault(journal_item, {
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


    def _get_gstr1_hsn_json(self, journal_items, tax_details_by_move):
        # TO OVERRIDE on Point of sale for get details by product
        """
            This method is return hsn json as below
            Here inovice line is group by product hsn code and product unit code and gst tax rate
            {'data': [{
                'num': 1,
                'hsn_sc': '94038900',
                'uqc': 'UNT',
                'rt': 5.0,
                'qty': 10.0,
                'txval': 40000.0,
                'iamt': 0.0,
                'samt': 1000.0,
                'camt': 1000.0,
                'csamt': 0.0
                }]
            }
        """
        uoms = self.env['uom.uom'].browse(journal_items.product_uom_id.ids)
        uoms.fetch(['l10n_in_code'])
        hsn_json = {}
        for move_id in journal_items.mapped('move_id'):
            # We sum value of invoice and credit note
            # so we need positive value for invoice and nagative for credit note
            tax_details = tax_details_by_move.get(move_id, {})
            for line, line_tax_details in tax_details.items():
                tax_rate = line_tax_details['gst_tax_rate']
                if tax_rate.is_integer():
                    tax_rate = int(tax_rate)
                uqc = uoms.browse(line.product_uom_id.id).l10n_in_code and uoms.browse(line.product_uom_id.id).l10n_in_code.split("-")[0] or "OTH"
                if line.product_id.type == 'service':
                    # If product is service then UQC is Not Applicable (NA)
                    uqc = "NA"
                group_key = "%s-%s-%s" %(
                    tax_rate, line.product_id.l10n_in_hsn_code, uqc)
                hsn_json.setdefault(group_key, {
                    "hsn_sc": self.env["account.edi.format"]._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code),
                    "uqc": uqc,
                    "rt": tax_rate,
                    "qty": 0.00, "txval": 0.00, "iamt": 0.00, "samt": 0.00, "camt": 0.00, "csamt": 0.00})
                if line.product_id.type != 'service':
                    if move_id.move_type in ('in_refund', 'out_refund'):
                        hsn_json[group_key]['qty'] -= line.quantity
                    else:
                        hsn_json[group_key]['qty'] += line.quantity
                hsn_json[group_key]['txval'] += line_tax_details.get('base_amount', 0.00) * -1
                hsn_json[group_key]['iamt'] += line_tax_details.get('igst', 0.00) * -1
                hsn_json[group_key]['samt'] += line_tax_details.get('cgst', 0.00) * -1
                hsn_json[group_key]['camt'] += line_tax_details.get('sgst', 0.00) * -1
                hsn_json[group_key]['csamt'] += line_tax_details.get('cess', 0.00) * -1
        return hsn_json

    def _get_gstr1_json(self):
        def _group_aml(group_by_field, journal_items):
            values = {}
            journal_items = journal_items.sorted(lambda l: l.mapped(group_by_field))
            for groupby_key, grouped_items in groupby(journal_items, lambda l: l.mapped(group_by_field)):
                values.setdefault(groupby_key, AccountMoveLine)
                for grouped_item in grouped_items:
                    values[groupby_key] += grouped_item
            return values

        def _get_b2b_json(journal_items):
            """
            This method is return b2b json as below
            Here itms is group by of invoice line per gst tax rate
            [{
                'ctin': '24AACCT6304M1ZB',
                'inv': [{
                    'inum': 'INV/2022/00005',
                    'idt': '01-04-2022',
                    'val': 100.00,
                    'pos': '24',
                    'rchrg': 'N',
                    'inv_typ': 'R',
                    'etin': "34AACCT6304M1ZB",
                    'diff_percent': 0.65,
                    'itms': [{
                        'num': 1,
                        'itm_det': {
                          'rt': 28.0,
                          'txval': 100.0,
                          'iamt': 0.0,
                          'samt': 9.0,
                          'camt': 9.0,
                          'csamt': 6.5
                        }
                    }]
                }]
            }]
            """
            b2b_json = []
            for partner, journal_items in _group_aml('move_id.commercial_partner_id', journal_items).items():
                inv_json_list = []
                for move_id in journal_items.mapped('move_id'):
                    lines_json = {}
                    is_reverse_charge = False
                    is_igst_amount = False
                    tax_details = tax_details_by_move.get(move_id)
                    for line_tax_details in tax_details.values():
                        line_all_tax_type = {line_td['tax_type'] for line_td in line_tax_details['line_tax_details']}

                        # Ignore the lines if invoice is not SEZ and GST taxes are not selected
                        if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not any(tax_type in line_all_tax_type for tax_type in ['IGST', 'CGST', 'SGST']):
                            continue
                        tax_rate = line_tax_details['gst_tax_rate']
                        if line_tax_details['l10n_in_reverse_charge']:
                            is_reverse_charge = True
                        lines_json.setdefault(tax_rate, {
                            "rt": tax_rate, "txval": 0.00, "iamt": 0.00, "samt": 0.00, "camt": 0.00, "csamt": 0.00})
                        if line_tax_details['igst']:
                            is_igst_amount = True
                        lines_json[tax_rate]['txval'] += line_tax_details['base_amount'] * -1
                        lines_json[tax_rate]['iamt'] += line_tax_details['igst'] * -1
                        lines_json[tax_rate]['camt'] += line_tax_details['cgst'] * -1
                        lines_json[tax_rate]['samt'] += line_tax_details['sgst'] * -1
                        lines_json[tax_rate]['csamt'] += line_tax_details['cess'] * -1
                    if lines_json:
                        invoice_type = 'R'
                        if move_id.l10n_in_gst_treatment == 'deemed_export':
                            invoice_type = 'DE'
                        elif move_id.l10n_in_gst_treatment == "special_economic_zone" and is_igst_amount:
                            invoice_type = 'SEWP'
                        elif move_id.l10n_in_gst_treatment == "special_economic_zone":
                            invoice_type = 'SEWOP'
                        inv_json = {
                            "inum": move_id.name,
                            "idt": move_id.invoice_date.strftime("%d-%m-%Y"),
                            "val": AccountEdiFormat._l10n_in_round_value(move_id.amount_total_in_currency_signed),
                            "pos": move_id.l10n_in_state_id.l10n_in_tin,
                            "rchrg": is_reverse_charge and "Y" or "N",
                            "inv_typ": invoice_type,
                            #"etin": move_id.l10n_in_reseller_partner_id.vat or "",
                            "itms": [
                                {"num": index, "itm_det": {
                                    'txval': AccountEdiFormat._l10n_in_round_value(line_json.pop('txval')),
                                    'iamt': AccountEdiFormat._l10n_in_round_value(line_json.pop('iamt')),
                                    'camt': AccountEdiFormat._l10n_in_round_value(line_json.pop('camt')),
                                    'samt': AccountEdiFormat._l10n_in_round_value(line_json.pop('samt')),
                                    'csamt': AccountEdiFormat._l10n_in_round_value(line_json.pop('csamt')), **line_json}}
                                for index, line_json in enumerate(lines_json.values(), start=1)
                            ],
                        }
                        inv_json_list.append(inv_json)
                b2b_json.append({'ctin': partner.vat, 'inv': inv_json_list})
            return b2b_json

        def _get_b2cl_json(journal_items):
            """
            This method is return b2cl json as below
            Here itms is group by of invoice line per gst tax rate
            [{
                'pos': '30',
                'inv': [{
                    'inum': 'INV/2022/00005',
                    'idt': '01-04-2022',
                    'val': 100.00,
                    'diff_percent': 0.65,
                    'itms': [{
                        'num': 1,
                        'itm_det': {
                          'rt': 28.0,
                          'txval': 100.0,
                          'iamt': 0.0,
                          'csamt': 6.5
                        }
                    }]
                }]
            }]
            """
            b2cl_json = []
            for state_id, journal_items in _group_aml('move_id.l10n_in_state_id', journal_items).items():
                inv_json_list = []
                for move_id in journal_items.mapped('move_id'):
                    lines_json = {}
                    tax_details = tax_details_by_move.get(move_id)
                    for line_tax_details in tax_details.values():
                        line_all_tax_type = {line_td['tax_type'] for line_td in line_tax_details['line_tax_details']}
                        if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not any(tax_type in line_all_tax_type for tax_type in ['IGST', 'CGST', 'SGST']):
                            continue
                        tax_rate = line_tax_details.get('gst_tax_rate')
                        lines_json.setdefault(tax_rate, {
                            "rt": tax_rate, "txval": 0.00, "iamt": 0.00, "csamt": 0.00})
                        lines_json[tax_rate]['txval'] += line_tax_details['base_amount'] * -1
                        lines_json[tax_rate]['iamt'] += line_tax_details['igst'] * -1
                        lines_json[tax_rate]['csamt'] += line_tax_details['cess'] * -1
                    if lines_json:
                        inv_json = {
                            "inum": move_id.name,
                            "idt": move_id.invoice_date.strftime("%d-%m-%Y"),
                            "val": AccountEdiFormat._l10n_in_round_value(move_id.amount_total_in_currency_signed),
                            #"etin": move_id.l10n_in_reseller_partner_id.vat or "",
                            "itms": [
                                {"num": index, "itm_det": {
                                    'txval': AccountEdiFormat._l10n_in_round_value(line_json.pop('txval')),
                                    'iamt': AccountEdiFormat._l10n_in_round_value(line_json.pop('iamt')),
                                    'csamt': AccountEdiFormat._l10n_in_round_value(line_json.pop('csamt')), **line_json}}
                                for index, line_json in enumerate(lines_json.values(), start=1)
                            ],
                        }
                        inv_json_list.append(inv_json)
                b2cl_json.append({'pos': state_id.l10n_in_tin, 'inv': inv_json_list})
            return b2cl_json

        def _get_b2cs_json(journal_items):
            """
            This method is return b2cs json as below
            Here data is group by gst tax rate and place of supply
            [{
              'sply_ty': 'INTRA',
              'pos': '36',
              'typ': 'OE',
              'rt': 5.0,
              'txval': 100,
              'iamt': 0.0,
              'samt': 2.50,
              'camt': 2.50,
              'csamt': 0.0
            }]
            """
            b2cs_json = {}
            for move_id in journal_items.mapped('move_id'):
                # We sum value of invoice and credit note
                # so we need positive value for invoice and nagative for credit note
                tax_details = tax_details_by_move.get(move_id)
                for line_tax_details in tax_details.values():
                    line_all_tax_type = {line_td['tax_type'] for line_td in line_tax_details['line_tax_details']}
                    if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not any(tax_type in line_all_tax_type for tax_type in ['IGST', 'CGST', 'SGST']):
                        continue
                    tax_rate = line_tax_details.get('gst_tax_rate')
                    group_key = "%s-%s"%(tax_rate, move_id.l10n_in_state_id.l10n_in_tin)
                    b2cs_json.setdefault(group_key, {
                        "sply_ty": move_id.l10n_in_state_id == move_id.company_id.state_id and "INTRA" or "INTER",
                        "pos": move_id.l10n_in_state_id.l10n_in_tin,
                        "typ": "OE",
                        "rt": tax_rate,
                        "txval": 0.00, "iamt": 0.00, "samt": 0.00, "camt": 0.00, "csamt": 0.00})
                    b2cs_json[group_key]['txval'] += line_tax_details['base_amount'] * -1
                    b2cs_json[group_key]['iamt'] += line_tax_details['igst'] * -1
                    b2cs_json[group_key]['camt'] += line_tax_details['cgst'] * -1
                    b2cs_json[group_key]['samt'] += line_tax_details['sgst'] * -1
                    b2cs_json[group_key]['csamt'] += line_tax_details['cess'] * -1
            return list({
                **d,
                "txval": AccountEdiFormat._l10n_in_round_value(d['txval']),
                "iamt": AccountEdiFormat._l10n_in_round_value(d['iamt']),
                "samt": AccountEdiFormat._l10n_in_round_value(d['samt']),
                "camt": AccountEdiFormat._l10n_in_round_value(d['camt']),
                "csamt": AccountEdiFormat._l10n_in_round_value(d['csamt']),
            } for d in b2cs_json.values())

        def _get_cdnr_json(journal_items):
            """
            This method is return cdnr json as below
            Here itms is group by of invoice line per gst tax rate
            [{
                'ctin': '24AACCT6304M1ZB',
                'nt': [{
                    'ntty': 'C',
                    'nt_num': 'RINV/2022/00001',
                    'nt_dt': '02-04-2022',
                    'val': 105296.77,
                    'pos': '24',
                    'rchrg': 'N',
                    'inv_typ': 'R',
                    'diff_percent': 0.65,
                    'itms': [{
                        'num': 1,
                        'itm_det': {
                          'rt': 28.0,
                          'txval': 80000.0,
                          'iamt': 0.0,
                          'samt': 11200.0,
                          'camt': 11200.0,
                          'csamt': 0.0
                        }
                    }]
                }]
            }]
            """
            cdnr_json = []
            for partner, journal_items in _group_aml('move_id.commercial_partner_id', journal_items).items():
                inv_json_list = []
                for move_id in journal_items.mapped('move_id'):
                    lines_json = {}
                    is_igst_amount = False
                    is_reverse_charge = False
                    tax_details = tax_details_by_move[move_id]
                    for line_tax_details in tax_details.values():
                        line_all_tax_type = {line_td['tax_type'] for line_td in line_tax_details['line_tax_details']}
                        if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not any(tax_type in line_all_tax_type for tax_type in ['IGST', 'CGST', 'SGST']):
                            continue
                        tax_rate = line_tax_details['gst_tax_rate']
                        if line_tax_details['l10n_in_reverse_charge']:
                            is_reverse_charge = True
                        if line_tax_details['igst']:
                            is_igst_amount = True
                        lines_json.setdefault(tax_rate, {
                            "rt": tax_rate, "txval": 0.00, "iamt": 0.00, "samt": 0.00, "camt": 0.00, "csamt": 0.00})
                        lines_json[tax_rate]['txval'] += line_tax_details['base_amount']
                        lines_json[tax_rate]['iamt'] += line_tax_details['igst']
                        lines_json[tax_rate]['samt'] += line_tax_details['cgst']
                        lines_json[tax_rate]['camt'] += line_tax_details['sgst']
                        lines_json[tax_rate]['csamt'] += line_tax_details['cess']
                    if lines_json:
                        invoice_type = 'R'
                        if move_id.l10n_in_gst_treatment == 'deemed_export':
                            invoice_type = 'DE'
                        elif move_id.l10n_in_gst_treatment == "special_economic_zone" and is_igst_amount:
                            invoice_type = 'SEWP'
                        elif move_id.l10n_in_gst_treatment == "special_economic_zone":
                            invoice_type = 'SEWOP'
                        inv_json = {
                            "ntty": "C",
                            "nt_num": move_id.name,
                            "nt_dt": move_id.invoice_date.strftime("%d-%m-%Y"),
                            "val": AccountEdiFormat._l10n_in_round_value(move_id.amount_total_in_currency_signed * -1),
                            "pos": move_id.l10n_in_state_id.l10n_in_tin,
                            "rchrg": is_reverse_charge and "Y" or "N",
                            "inv_typ": invoice_type,
                            "itms": [
                                {"num": index, "itm_det": {
                                    **line_json,
                                    "txval": AccountEdiFormat._l10n_in_round_value(line_json['txval']),
                                    "iamt": AccountEdiFormat._l10n_in_round_value(line_json['iamt']),
                                    "samt": AccountEdiFormat._l10n_in_round_value(line_json['samt']),
                                    "camt": AccountEdiFormat._l10n_in_round_value(line_json['camt']),
                                    "csamt": AccountEdiFormat._l10n_in_round_value(line_json['csamt']),
                                }} for index, line_json in enumerate(lines_json.values(), start=1)
                            ],
                        }
                        inv_json_list.append(inv_json)
                cdnr_json.append({'ctin': partner.vat, 'nt': inv_json_list})
            return cdnr_json

        def _get_cdnur_json(journal_items):
            """
            This method is return cdnur json as below
            Here itms is group by of invoice line per gst tax rate
            [{
                'ntty': 'C',
                'nt_num': 'RINV/2022/00002',
                'nt_dt': '02-05-2022',
                'val': 212400.0,
                'pos': '30',
                'typ': 'B2CL',
                'diff_percent': 0.65,
                'itms': [{
                    'num': 1,
                    'itm_det': {
                      'rt': 18.0,
                      'txval': 180000.0,
                      'iamt': 32400.0,
                      'csamt': 0.0
                    }
                }]
            }]
            """
            inv_json_list = []
            for move_id in journal_items.mapped('move_id'):
                tax_details = tax_details_by_move.get(move_id)
                lines_json = {}
                is_igst_amount = False
                for line_tax_detail in tax_details.values():
                    line_all_tax_type = {line_td['tax_type'] for line_td in line_tax_detail['line_tax_details']}
                    if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not any(tax_type in line_all_tax_type for tax_type in ['IGST', 'CGST', 'SGST']):
                        continue
                    if line_tax_detail['igst']:
                        is_igst_amount = True
                    tax_rate = line_tax_detail['gst_tax_rate']
                    lines_json.setdefault(tax_rate, {
                        "rt": tax_rate, "txval": 0.00, "iamt": 0.00, "csamt": 0.00})
                    lines_json[tax_rate]['txval'] += line_tax_detail['base_amount']
                    lines_json[tax_rate]['iamt'] += line_tax_detail['igst']
                    lines_json[tax_rate]['csamt'] += line_tax_detail['cess']
                if lines_json:
                    invoice_type = 'B2CL'
                    if move_id.l10n_in_gst_treatment == "overseas" and is_igst_amount:
                        invoice_type = 'EXPWP'
                    elif move_id.l10n_in_gst_treatment == "overseas":
                        invoice_type = 'EXPWOP'
                    inv_json = {
                        "ntty": move_id.move_type == "out_refund" and "C" or "D",
                        "nt_num": move_id.name,
                        "nt_dt": move_id.invoice_date.strftime("%d-%m-%Y"),
                        "val": AccountEdiFormat._l10n_in_round_value(move_id.amount_total_signed * -1),
                        "typ": invoice_type,
                        "itms": [
                            {"num": index, "itm_det": {
                                **line_json,
                                "txval": AccountEdiFormat._l10n_in_round_value(line_json['txval']),
                                "iamt": AccountEdiFormat._l10n_in_round_value(line_json['iamt']),
                                "csamt": AccountEdiFormat._l10n_in_round_value(line_json['csamt']),
                            }} for index, line_json in enumerate(lines_json.values(), start=1)
                        ],
                    }
                    if invoice_type == 'B2CL':
                        inv_json.update({"pos": move_id.l10n_in_state_id.l10n_in_tin})
                    inv_json_list.append(inv_json)
            return inv_json_list

        def _get_exp_json(journal_items):
            """
            This method is return exp json as below
            Here itms is group by of invoice line per gst tax rate
            [{
                'exp_typ': 'WPAY',
                'inv': [{
                    'inum': 'INV/2022/00008',
                    'idt': '01-04-2022',
                    'val': 283200.0,
                    'sbnum': '999704',
                    'sbdt': '02/04/2022',
                    'sbpcode': 'INIXY1',
                    'itms': [
                    {
                        'rt': 18.0,
                        'txval': 240000.0,
                        'iamt': 43200.0,
                        'csamt': 0.0
                    }]
                }]
            }]
            """
            export_json = {}
            for move_id in journal_items.mapped('move_id'):
                tax_details = tax_details_by_move.get(move_id)
                lines_json = {}
                is_igst_amount = False
                for line_tax_details in tax_details.values():
                    if line_tax_details['igst']:
                        is_igst_amount = True
                    tax_rate = line_tax_details['gst_tax_rate']
                    lines_json.setdefault(tax_rate, {"rt": tax_rate, "txval": 0.00, "iamt": 0.00, "csamt": 0.00})
                    lines_json[tax_rate]['txval'] += line_tax_details['base_amount'] * -1
                    lines_json[tax_rate]['iamt'] += line_tax_details['igst'] * -1
                    lines_json[tax_rate]['csamt'] += line_tax_details['cess'] * -1
                if lines_json:
                    invoice_type = 'WOPAY'
                    if is_igst_amount:
                        invoice_type = 'WPAY'
                    export_json.setdefault(invoice_type, [])
                    export_inv = {
                        "inum": move_id.name,
                        "idt": move_id.invoice_date.strftime("%d-%m-%Y"),
                        "val": AccountEdiFormat._l10n_in_round_value(move_id.amount_total_signed),
                        "itms": list({
                            **d,
                            "txval": AccountEdiFormat._l10n_in_round_value(d['txval']),
                            "iamt": AccountEdiFormat._l10n_in_round_value(d['iamt']),
                            "csamt": AccountEdiFormat._l10n_in_round_value(d['csamt']),
                            }
                            for d in lines_json.values()),
                    }
                    if move_id.l10n_in_shipping_bill_number:
                        export_inv.update({"sbnum": move_id.l10n_in_shipping_bill_number})
                    if move_id.l10n_in_shipping_bill_date:
                        export_inv.update({"sbdt": move_id.l10n_in_shipping_bill_date.strftime("%d-%m-%Y")})
                    if move_id.l10n_in_shipping_port_code_id.code:
                        export_inv.update({"sbpcode": move_id.l10n_in_shipping_port_code_id.code})
                    export_json[invoice_type].append(export_inv)
            return [{"exp_typ":invoice_type, "inv": inv_json} for invoice_type, inv_json in export_json.items()]

        def _get_nil_json(journal_items):
            """
            This method is return nil json as below
            Here data is grouped by supply_type and sum of base amount of diffrent type of 0% tax
            {
                'inv':[{
                    'sply_ty': 'INTRB2B',
                    'nil_amt': 100.0,
                    'expt_amt': 200.0,
                    'ngsup_amt': 300.0,
                }]
            }
            """
            nil_json = {}
            nil_tag_ids = self.env.ref('l10n_in.tax_tag_nil_rated')
            exempt_tag_ids = self.env.ref('l10n_in.tax_tag_exempt')
            non_gst_tag_ids = self.env.ref('l10n_in.tax_tag_non_gst_supplies')
            for move_id in journal_items.mapped('move_id'):
                # We sum value of invoice and credit note
                # so we need positive value for invoice and nagative for credit note
                tax_details = tax_details_by_move.get(move_id, {})
                same_state = move_id.l10n_in_state_id == move_id.company_id.state_id
                supply_type = ""
                if same_state:
                    if move_id.l10n_in_gst_treatment in ('special_economic_zone', 'deemed_export', 'regular'):
                        supply_type = "INTRAB2B"
                    else:
                        supply_type = "INTRAB2C"
                else:
                    if move_id.l10n_in_gst_treatment in ('special_economic_zone', 'deemed_export', 'regular'):
                        supply_type = "INTRB2B"
                    else:
                        supply_type = "INTRB2C"
                nil_json.setdefault(supply_type, {
                    "sply_ty": supply_type,
                    "nil_amt": 0.00,
                    "expt_amt": 0.00,
                    "ngsup_amt": 0.00,
                })
                for line, line_tax_detail  in tax_details.items():
                    base_line_tag_ids = line.tax_tag_ids
                    if any(tag_id in base_line_tag_ids for tag_id in nil_tag_ids):
                        nil_json[supply_type]['nil_amt'] += line_tax_detail['base_amount'] * -1
                    if any(tag_id in base_line_tag_ids for tag_id in exempt_tag_ids):
                        nil_json[supply_type]['expt_amt'] += line_tax_detail['base_amount'] * -1
                    if any(tag_id in base_line_tag_ids for tag_id in non_gst_tag_ids):
                        nil_json[supply_type]['ngsup_amt'] += line_tax_detail['base_amount'] * -1
            return nil_json and {'inv': list({
                **d,
                "nil_amt": AccountEdiFormat._l10n_in_round_value(d['nil_amt']),
                "expt_amt": AccountEdiFormat._l10n_in_round_value(d['expt_amt']),
                "ngsup_amt": AccountEdiFormat._l10n_in_round_value(d['ngsup_amt']),
            } for d in nil_json.values())} or {}

        AccountMoveLine = self.env['account.move.line']
        AccountEdiFormat = self.env["account.edi.format"]
        tax_details_by_move = self._get_tax_details(self._get_section_domain('hsn'))
        hsn_json = self._get_gstr1_hsn_json(AccountMoveLine.search(self._get_section_domain('hsn')), tax_details_by_move)
        nil_json = _get_nil_json(AccountMoveLine.search(self._get_section_domain('nil')))
        return_json = {
            'gstin': self.tax_unit_id.vat or self.company_id.vat,
            'fp': self.return_period_month_year,
            'b2b': _get_b2b_json(AccountMoveLine.search(self._get_section_domain('b2b'))),
            'b2cl': _get_b2cl_json(AccountMoveLine.search(self._get_section_domain('b2cl'))),
            'b2cs': _get_b2cs_json(AccountMoveLine.search(self._get_section_domain('b2cs'))),
            'cdnr': _get_cdnr_json(AccountMoveLine.search(self._get_section_domain('cdnr'))),
            'cdnur': _get_cdnur_json(AccountMoveLine.search(self._get_section_domain('cdnur'))),
            'exp': _get_exp_json(AccountMoveLine.search(self._get_section_domain('exp')))
        }
        if nil_json:
            return_json.update({'nil': nil_json})
        if hsn_json:
            return_json.update({'hsn':
                {'data': [{**hsn_dict, 'num': index,
                    'txval': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('txval')),
                    'iamt': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('iamt')),
                    'camt': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('camt')),
                    'samt': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('samt')),
                    'csamt': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('csamt')),
                    'qty': AccountEdiFormat._l10n_in_round_value(hsn_dict.get('qty')),
                    } for index, hsn_dict in enumerate(hsn_json.values(), start=1)]}})
        return return_json

    def button_send_gstr1(self):
        self._check_config()
        self.sudo().write({
            "gstr1_error": False,
            "gstr1_blocking_level": False,
            "gstr1_status": "sending",
        })
        self.env.ref("l10n_in_reports_gstr.ir_cron_to_send_gstr1_data")._trigger()

    def _cron_send_gstr1_data(self, job_count=None):
        gstr1_sending = self.search([("gstr1_status", "=", "sending")])
        process_gstr1 = gstr1_sending[:job_count] if job_count else gstr1_sending
        for return_period in process_gstr1:
            return_period.send_gstr1()
            if len(process_gstr1) > 1:
                self._cr.commit()
        if process_gstr1:
            self.env.ref("l10n_in_reports_gstr.ir_cron_to_check_gstr1_status")._trigger(fields.Datetime.now() + timedelta(minutes=1))
        if len(process_gstr1) != len(gstr1_sending):
            self.env.ref("l10n_in_reports_gstr.ir_cron_to_send_gstr1_data")._trigger()

    def send_gstr1(self):
        json_payload = self._get_gstr1_json()
        self.sudo().message_post(
            subject=_("GSTR-1 Send data"),
            body=_("Json file that send to Government is attached here"),
            attachments=[("status_response.json", json.dumps(json_payload))])
        response = self._send_gstr1(
            company=self.company_id,
            json_payload=json_payload,
            month_year=self.return_period_month_year)
        if response.get("data"):
            self.sudo().write({
                "gstr1_status": "waiting_for_status",
                "gstr_reference": response["data"].get("reference_id"),
            })
        elif response.get("error"):
            error_codes = [e.get('code') for e in response["error"]]
            error_msg = ""
            if 'no-credit' in error_codes:
                error_msg = self.env["account.edi.format"]._l10n_in_edi_get_iap_buy_credits_message(self.company_id)
            else:
                error_msg = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in response["error"]])
            self.sudo().write({
                "gstr1_blocking_level": self._get_error_lavel(error_codes),
                "gstr1_error": error_msg,
            })
        else:
            self.sudo().write({
                "gstr1_blocking_level": "error",
                "gstr1_error": "Something is wrong in response. Please contact support. \n response: %s"%(response),
            })

    def button_check_gstr1_status(self):
        self.ensure_one()
        if self.gstr1_status != "waiting_for_status":
            raise AccessError(_("TO check status please push the GSTN"))
        self._check_config()
        self.check_gstr1_status()

    def check_gstr1_status(self):
        response = self._get_gstr_status(
            company=self.company_id, month_year=self.return_period_month_year, reference_id=self.gstr_reference)
        if response.get('data'):
            advisor_user = self.env['res.users'].search([
                ('company_ids', 'in', self.company_ids.ids or self.company_id.ids),
                ('groups_id', 'in', self.env.ref('account.group_account_manager').ids)], limit=1, order="id ASC")
            data = response["data"]
            if data.get("status_cd") == "P":
                self.sudo().write({
                    "gstr1_error": False,
                    "gstr1_blocking_level": False,
                    "gstr1_status": "sent",
                })
                odoobot = self.env.ref('base.partner_root')
                self.sudo().message_post(body=_("GSTR-1 Successfully Sent"), author_id=odoobot.id)
            elif data.get("status_cd") == "IP":
                self.sudo().write({
                    "gstr1_error": "Waiting for GSTR-1 processing, try in a few minutes",
                    "gstr1_blocking_level": "warning"
                })
            elif data.get("status_cd") in ("PE", "ER"):
                self.sudo().write({
                    "gstr1_error": False,
                    "gstr1_blocking_level": False,
                    "gstr1_status": "error_in_invoice",
                })
                message = ""
                AccountMove = self.env['account.move'].with_context(allowed_company_ids=self.company_ids.ids)
                if data.get("status_cd") == "ER":
                    error_report = data.get('error_report', {})
                    message = "[%s] %s"%(error_report.get('error_cd'), error_report.get('error_msg'))
                else:
                    for section_code, inv_by_section in data.get('error_report').items():
                        message += "<li><b>%s :- </b></li>"%(section_code.upper())
                        for invoice in inv_by_section:
                            error_cd = invoice.get('error_cd', False)
                            error_msg = invoice.get('error_msg', False)
                            invoice_number = ""
                            if error_cd or error_msg:
                                if section_code in ('b2b', 'b2cl', 'exp'):
                                    invoice_number = invoice.get('inv')[0].get('inum')
                                if section_code == "cdnr":
                                    invoice_number = invoice.get('nt')[0].get('nt_num')
                                if section_code == 'cdnur':
                                    invoice_number = invoice.get('nt_num')
                                msg = " - ".join([error_cd, error_msg])
                                moves = AccountMove.search([('name', '=', invoice_number),
                                    ('company_id', 'in', self.company_ids.ids or self.company_id.ids)])
                                for move in moves:
                                    invoice_link_msg = "".join(
                                        "<a href='#' data-oe-model='account.move' data-oe-id='%s'>%s</a>"
                                        %(move.id, move.name))
                                    message += "<ul><li>Invoice :- %s</li>" %(invoice_link_msg)
                                    message += "<ul><li> %s </li></ul></ul>" %(msg)
                                    # Create activity in Invoice
                                    move.activity_schedule(
                                        act_type_xmlid='mail.mail_activity_data_warning',
                                        user_id=advisor_user.id or self.env.user.id,
                                        note=_('GSTR-1 Processed with Error:<b>%s</b>', msg))
                                message += "<ul><li>%s</li></ul>" %(msg) if not moves else ""

                # Create message in Return period
                self.sudo().message_post(
                    subject=_("GSTR-1 Errors"),
                    body=_('%s', message),
                    attachments=[("status_response.json", json.dumps(response))])
            else:
                self.sudo().write({
                    "gstr1_blocking_level": "error",
                    "gstr1_error": "Something is wrong in response. Please contact support. \n response: %s"%(response),
                })

        elif response.get("error"):
            error_msg = ""
            error_codes = [e.get('code') for e in response["error"]]
            if 'no-credit' in error_codes:
                error_msg = self.env["account.edi.format"]._l10n_in_edi_get_iap_buy_credits_message(self.company_id)
            else:
                error_msg = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in response["error"]])
            self.sudo().write({
                "gstr1_blocking_level": self._get_error_lavel(error_codes),
                "gstr1_error": error_msg,
            })
        else:
            self.sudo().write({
                "gstr1_blocking_level": "error",
                "gstr1_error": "Something is wrong in response. Please contact support",
            })

    def _cron_check_gstr1_status(self):
        sent_rtn = self.search([("gstr1_status", "=", "waiting_for_status")])
        for rtn in sent_rtn:
            rtn.check_gstr1_status()

    def _get_section_domain(self, section_code):
        sgst_tag_ids = self.env.ref('l10n_in.tax_tag_base_sgst').ids + self.env.ref('l10n_in.tax_tag_sgst').ids
        cgst_tag_ids = self.env.ref('l10n_in.tax_tag_base_cgst').ids + self.env.ref('l10n_in.tax_tag_cgst').ids
        igst_tag_ids = self.env.ref('l10n_in.tax_tag_base_igst').ids + self.env.ref('l10n_in.tax_tag_igst').ids
        cess_tag_ids = (
            self.env.ref('l10n_in.tax_tag_base_cess').ids
            + self.env.ref('l10n_in.tax_tag_cess').ids)
        zero_rated_tag_ids = self.env.ref('l10n_in.tax_tag_zero_rated').ids
        gst_tags = sgst_tag_ids + cgst_tag_ids + igst_tag_ids + cess_tag_ids + zero_rated_tag_ids
        other_than_gst_tag = (
            self.env.ref("l10n_in.tax_tag_exempt").ids
            + self.env.ref("l10n_in.tax_tag_nil_rated").ids
            + self.env.ref("l10n_in.tax_tag_non_gst_supplies").ids
        )
        export_tags = igst_tag_ids + zero_rated_tag_ids + cess_tag_ids + other_than_gst_tag
        domain = [
            ("date", ">=", self.start_date),
            ("date", "<=", self.end_date),
            ("move_id.state", "=", "posted"),
            ("company_id", "in", self.company_ids.ids or self.company_id.ids),
            ("display_type", "not in", ('rounding', 'line_note', 'line_section'))
        ]
        if section_code == "b2b":
            return (
                domain
                + [
                    ("move_id.move_type", "in", ["out_invoice", "out_receipt"]),
                    "|", '&',
                    ("move_id.l10n_in_gst_treatment", "in", ("regular", "deemed_export", "uin_holders", "composition")),
                    ("tax_tag_ids", "in", gst_tags),
                    '&',
                    ("move_id.l10n_in_gst_treatment", "=", "special_economic_zone"),
                    ("tax_tag_ids", "in", gst_tags + other_than_gst_tag),
                ]
            )
        if section_code == "b2cl":
            return (
                domain
                + [
                    ("move_id.move_type", "in", ["out_invoice", "out_receipt"]),
                    ("move_id.l10n_in_gst_treatment", "in", ("unregistered", "consumer")),
                    ("move_id.l10n_in_state_id", "!=", self.company_id.state_id.id),
                    ("move_id.amount_total", ">", 250000),
                    ("tax_tag_ids", "in", gst_tags),
                ]
            )
        if section_code == "b2cs":
            return (
                domain
                + [
                    ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                    ("move_id.l10n_in_gst_treatment", "in", ("unregistered", "consumer")),
                    ("tax_tag_ids", "in", gst_tags),
                    "|",
                    ("move_id.l10n_in_transaction_type", "=", "intra_state"),
                    "&",
                    ("move_id.l10n_in_transaction_type", "=", "inter_state"),
                    ("move_id.amount_total", "<=", 250000),
                ]
            )
        if section_code == "cdnr":
            return (
                domain
                + [
                    ("move_id.move_type", "=", "out_refund"),
                    "|", '&',
                    ("move_id.l10n_in_gst_treatment", "in", ("regular", "deemed_export", "uin_holders", "composition")),
                    ("tax_tag_ids", "in", gst_tags),
                    '&',
                    ("move_id.l10n_in_gst_treatment", "=", "special_economic_zone"),
                    ("tax_tag_ids", "in", gst_tags + other_than_gst_tag),
                ]
            )
        if section_code == "cdnur":
            return (
                domain
                + [
                    ("move_id.move_type", "=", "out_refund"),
                    "|", "&",
                    ("move_id.l10n_in_gst_treatment", "=", "overseas"),
                    ("tax_tag_ids", "in", export_tags),
                    "&", "&", "&",
                    ("tax_tag_ids", "in", gst_tags),
                    ("move_id.l10n_in_gst_treatment", "in", ["unregistered", "consumer"]),
                    ("move_id.l10n_in_transaction_type", "=", "inter_state"),
                    ("move_id.amount_total", ">", 250000),
                ]
            )
        if section_code == "exp":
            return (
                domain
                + [
                    ("move_id.move_type", "in", ["out_invoice", "out_receipt"]),
                    ("move_id.l10n_in_gst_treatment", "=", "overseas"),
                    ("tax_tag_ids", "in", export_tags),
                ]
            )
        if section_code == "nil":
            return (
                domain
                + [
                    ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                    ("move_id.l10n_in_gst_treatment", "not in", ["overseas", "special_economic_zone"]),
                    ("tax_tag_ids", "in", other_than_gst_tag),
                ]
            )
        if section_code == "hsn":
            return (
                domain
                + [
                    ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                    ("tax_tag_ids", "in", gst_tags + other_than_gst_tag),
                ]
            )

        raise UserError("Section %s is unkown" % (section_code))

    def action_view_gstr1_return_period(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("l10n_in_reports.action_account_report_gstr1")
        action.update({
            'params': {
                'options': {
                    'date': {
                        'date_from': self.start_date.strftime('%Y-%m-%d'),
                        'date_to': self.end_date.strftime('%Y-%m-%d'),
                        'filter': 'custom',
                        'mode':'range',
                    },
                    'l10n_in_tax_unit': self.tax_unit_id.id,
                },
                'ignore_session': True,
            }
        })
        return action

    def button_gstr1_filed(self):
        if self.gstr1_status != "sent":
            raise UserError(_("Before set as Filed, Status of GSTR-1 must be send"))
        self.gstr1_status = "filed"

    # ===============================
    # GSTR-2B
    # ===============================

    def action_get_gstr2b_view_reconciled_invoice(self):
        self.ensure_one()
        domain = [("l10n_in_gst_return_period_id", "=", self.id)]
        return {
            "name": _("Reconciled Bill"),
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            'context': {'create': False, "search_default_gstr2b_status": True},
            "domain": domain,
            "view_mode": "tree,form",
        }

    def action_get_gstr2b_data(self):
        self._check_config()
        self.sudo().write({
            "gstr2b_status": "waiting_reception",
            "gstr2b_error": False,
            "gstr2b_blocking_level": False,
        })
        self.env.ref('l10n_in_reports_gstr.ir_cron_auto_sync_gstr2b_data')._trigger()

    def get_gstr2b_data(self):
        response = self._get_gstr2b_data(company=self.company_id, month_year=self.return_period_month_year)
        if response.get("data"):
            gstr2b_data = response["data"]
            attachment_ids = self.env['ir.attachment'].create({
                'name': 'gstr2b_0.json',
                'mimetype': 'application/json',
                'raw': json.dumps(response),
            })
            if gstr2b_data.get("data", {}).get('fc'):
                number_of_files = gstr2b_data.get("data", {}).get('fc') + 1
                for file_num in range(1, number_of_files):
                    sub_response = self._get_gstr2b_data(company=self.company_id, month_year=self.return_period_month_year, file_number=file_num)
                    if not sub_response.get('error'):
                        attachment_ids += self.env['ir.attachment'].create({
                            'name': 'gstr2b_%s.json' % (file_num),
                            'mimetype': 'application/json',
                            'raw': json.dumps(sub_response),
                        })
                    else:
                        response = sub_response
            self.sudo().gstr2b_json_from_portal_ids = attachment_ids
        if response.get('error'):
            error_msg = ""
            error_codes = [e.get('code') for e in response["error"]]
            if 'no-credit' in error_codes:
                error_msg = self.env["account.edi.format"]._l10n_in_edi_get_iap_buy_credits_message(self.company_id)
            else:
                error_msg = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in response["error"]])
            self.sudo().write({
                "gstr2b_blocking_level": self._get_error_lavel(error_codes),
                "gstr2b_error": error_msg,
            })
        else:
            self.sudo().gstr2b_status = "being_processed"

    def _cron_get_gstr2b_data(self):
        for return_period in self.search([('gstr2b_status', '=', 'waiting_reception')]):
            return_period.get_gstr2b_data()

    def convert_to_date(self, date):
        # can't use field.date.to_date because formate is different then DEFAULT_SERVER_DATE_FORMAT
        return datetime.strptime(date, "%d-%m-%Y").date()

    def _cron_gstr2b_match_data(self):
        return_periods = self.search([('gstr2b_status', '=', 'being_processed')])
        for return_period in return_periods:
            return_period.gstr2b_match_data()

    def gstr2b_match_data(self):
        """
            Matching GSTR-2B data with vendeors bills that bill date is in those return period
            and first match with the reference number and if reference number is match then try
            to match with invoice value, total amount and date of bill,
            if multipls reference found then add exceptions with that bill name,
            if there is no reference number found then metch with invoice value, total amount and date of bill
            and exceptions for reference number.
        """
        def _create_attachment(move, json_data, ref=None):
            return self.env['ir.attachment'].create({
                "name": "gstr2b_matching_data_%s.json"%(ref or move.ref),
                "raw": json.dumps(json_data),
                "res_model": move and "account.move" or False,
                "res_id": move and move.id or False,
                "mimetype": "application/json",
                })

        def match_bills(gstr2b_streamline_bills, matching_dict):
            create_vals = []
            checked_bills = self.env['account.move']
            for gstr2b_bill in gstr2b_streamline_bills:
                amount = gstr2b_bill.get('bill_total')
                if gstr2b_bill.get('bill_taxable_value'):
                    amount = gstr2b_bill.get('bill_taxable_value')
                matching_keys = _get_matching_keys(
                    gstr2b_bill.get('bill_number'), gstr2b_bill.get('vat'), gstr2b_bill.get('bill_date'),
                    gstr2b_bill.get('bill_type'), amount)
                matched_bills = False
                for matching_key in matching_keys:
                    if not matched_bills and matching_dict.get(matching_key):
                        matched_bills = matching_dict.get(matching_key)
                if matched_bills:
                    created_from_reconciliation = matched_bills.filtered(lambda b:
                        b.l10n_in_gstr2b_reconciliation_status == 'gstr2_bills_not_in_odoo' and b.state == 'draft')
                    checked_bills += created_from_reconciliation
                    matched_bills = matched_bills - created_from_reconciliation
                    if gstr2b_bill['bill_type'] == 'credit_note':
                        invoice_type = 'Credit Note'
                    else:
                        invoice_type = 'Bill'
                    if len(matched_bills) == 1:
                        exception = []
                        if matched_bills.ref == gstr2b_bill.get('bill_number'):
                            if 'bill_taxable_value' in gstr2b_bill and gstr2b_bill['bill_taxable_value'] != matched_bills.amount_untaxed:
                                exception.append(_("Total Taxable amount as per GSTR-2B is %s", gstr2b_bill['bill_taxable_value']))
                            amount_total = matched_bills.amount_total
                            sign = 1 if matched_bills.is_inbound(include_receipts=True) else -1
                            for line in matched_bills.line_ids:
                                if line.tax_line_id.amount < 0:
                                    amount_total += line.balance * sign
                            if 'bill_total' in gstr2b_bill and gstr2b_bill['bill_total'] != amount_total:
                                exception.append(_("Total amount as per GSTR-2B is %s", gstr2b_bill['bill_total']))
                            if 'vat' in gstr2b_bill and gstr2b_bill['vat'] != matched_bills.partner_id.vat:
                                exception.append(_("Vat number as per GSTR-2B is %s", gstr2b_bill['vat']))
                            if 'bill_date' in gstr2b_bill and gstr2b_bill['bill_date'] != matched_bills.invoice_date:
                                exception.append(_("Bill Date as per GSTR-2B is %s", gstr2b_bill['bill_date']))
                            if 'bill_type' in gstr2b_bill and (matched_bills.move_type == 'in_refund' and gstr2b_bill['bill_type'] == 'bill') or \
                                (matched_bills.move_type != 'in_refund' and gstr2b_bill['bill_type'] == 'credit_note'):
                                exception.append(_("Bill type as per GSTR-2B is %s", invoice_type))
                        elif (gstr2b_bill.get('bill_total') == matched_bills.amount_total or \
                            gstr2b_bill.get('bill_taxable_value') == matched_bills.amount_untaxed) and \
                            gstr2b_bill.get('vat') == matched_bills.partner_id.vat and \
                            gstr2b_bill.get('bill_date') == matched_bills.invoice_date and \
                            (matched_bills.move_type == 'in_refund' and gstr2b_bill.get('bill_type') == 'credit_note') or \
                            (matched_bills.move_type != 'in_refund' and gstr2b_bill.get('bill_type') == 'bill'):
                            exception.append(_("Referance number as per GSTR-2B is %s", gstr2b_bill['bill_number']))
                        matched_bills.write({
                            "l10n_in_exception": '<br/>'.join(exception),
                            "l10n_in_gstr2b_reconciliation_status": exception and "partially_matched" or "matched",
                            "l10n_in_gst_return_period_id": self.id,
                        })
                        checked_bills += matched_bills
                        _create_attachment(matched_bills, gstr2b_bill.get('bill_value_json'))
                    else:
                        for bill in matched_bills:
                            _create_attachment(bill, gstr2b_bill.get('bill_value_json'))
                            other_bills = Markup("<br/>").join(Markup("<a href='#' data-oe-model='account.move' data-oe-id='%s'>%s</a>") % (
                                    other_bill.id, other_bill.name) for other_bill in matched_bills - bill)
                            bill.message_post(
                            subject=_("GSTR-2B Reconciliation"),
                            body=_("Referance number is same other bills: %s", other_bills))
                        matched_bills.write({
                            "l10n_in_exception": "We find same referance in other bills. For more details check message in chatter.",
                            'l10n_in_gstr2b_reconciliation_status': "bills_not_in_gstr2",
                            "l10n_in_gst_return_period_id": self.id,
                        })
                        checked_bills += matched_bills
                else:
                    partner = 'vat' in gstr2b_bill and self.env['res.partner'].search([
                        *self.env['res.partner']._check_company_domain(self.company_id),
                        ('vat', '=', gstr2b_bill['vat']),
                    ], limit=1)
                    journal = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(self.company_id),
                        ('type', '=', 'purchase')
                    ], limit=1)
                    default_l10n_in_gst_treatment = (gstr2b_bill.get('section_code') == 'impg' and 'overseas') or (gstr2b_bill.get('section_code') == 'impgsez' and 'special_economic_zone') or 'regular'
                    create_vals.append({
                        "move_type": gstr2b_bill.get('bill_type') == 'credit_note' and "in_refund" or "in_invoice",
                        "ref": gstr2b_bill.get('bill_number'),
                        "invoice_date": gstr2b_bill.get('bill_date'),
                        "partner_id": partner.id,
                        "l10n_in_gst_treatment": partner and partner.l10n_in_gst_treatment in ('deemed_export', 'uin_holders') and partner.l10n_in_gst_treatment or default_l10n_in_gst_treatment,
                        "journal_id": journal.id,
                        "l10n_in_gstr2b_reconciliation_status": "gstr2_bills_not_in_odoo",
                        "to_check": True,
                        "l10n_in_gst_return_period_id": self.id,
                        "message_ids":[(0, 0, {
                            'model': 'account.move',
                            'body': _(
                                "This Bill is Created from GSTR2B Reconciliation because no bill matched with given details"
                            ),
                            'attachment_ids': _create_attachment(
                                self.env['account.move'],
                                gstr2b_bill.get('bill_value_json'),
                                ref=gstr2b_bill.get('bill_number')
                            ).ids
                        })]
                    })
            if create_vals:
                created_move = self.env['account.move'].create(create_vals)
                checked_bills += created_move
            return checked_bills

        def _get_matching_keys(ref, vat, invoice_date, invoice_type, amount):
            # remove space from ref
            ref = ref and ref.replace(" ", "")
            return [
                "%s-%s-%s-%s-%s"%(ref, vat, invoice_type, invoice_date, amount), # Best case
                "%s-%s-%s-%s"%(ref, vat, invoice_type, invoice_date),
                "%s-%s-%s-%s"%(ref, vat, invoice_type, amount),
                "%s-%s-%s"%(ref, vat, invoice_type),

                "%s-%s-%s-%s"%(ref, vat, invoice_date, amount),
                "%s-%s-%s"%(ref, vat, invoice_date),
                "%s-%s-%s"%(ref, vat, amount),
                "%s-%s"%(ref, vat),

                "%s-%s-%s-%s"%(ref, invoice_type, invoice_date, amount),
                "%s-%s-%s"%(ref, invoice_type, invoice_date),
                "%s-%s-%s"%(ref, invoice_type, amount),
                "%s-%s"%(ref, invoice_type),

                "%s-%s-%s"%(ref, invoice_date, amount),
                "%s-%s"%(ref, invoice_date),
                "%s-%s"%(ref, amount),
                "%s"%(ref),
                "%s-%s-%s-%s"%(vat, invoice_type, invoice_date, amount) # Worst case
            ]

        def _get_all_bill_by_matching_key(gstr2b_late_streamline_bills):
            AccountMove = self.env["account.move"]
            matching_dict = {}
            domain = ['|',
                ("l10n_in_gst_return_period_id", "=", self.id),
                '&', ("move_type", "in", AccountMove.get_purchase_types()),
                '&', ("invoice_date", ">=", self.start_date),
                '&', ("invoice_date", "<=", self.end_date),
                '&', ("company_id", "in", self.company_ids.ids or self.company_id.ids),
                '&', ("state", "=", "posted"),
                     ("l10n_in_gst_treatment", "not in", ('composition', 'unregistered', 'consumer'))
            ]
            to_match_bills = AccountMove.search(domain)
            for late_bill in gstr2b_late_streamline_bills:
                to_match_bills += AccountMove.search([
                    ('l10n_in_gst_return_period_id', '!=', self.id),
                    ("invoice_date", "<", self.start_date),
                    ("company_id", "in", self.company_ids.ids or self.company_id.ids),
                    ("move_type", "in", AccountMove.get_purchase_types()),
                    ('ref', '=', late_bill.get('bill_number')),
                    ("state", "=", "posted"),
                    ("l10n_in_gst_treatment", "not in", ('composition', 'unregistered', 'consumer'))
                ])
            for bill in to_match_bills:
                bill_type = 'bill'
                amount = bill.amount_total
                # For SEZ and overseas amount get from Goverment is amount_untaxed
                if bill.l10n_in_gst_treatment in ('special_economic_zone', 'overseas'):
                    amount = bill.amount_untaxed
                if bill.move_type == 'in_refund':
                    bill_type = 'credit_note'
                matching_keys = _get_matching_keys(bill.ref, bill.partner_id.vat, bill.invoice_date, bill_type, amount)
                for matching_key in matching_keys:
                    matching_dict.setdefault(matching_key, AccountMove)
                    matching_dict[matching_key] += bill
            return to_match_bills, matching_dict

        def get_streamline_bills_from_json(json_payload):
            vals_list = []
            late_vals_list = []
            gstr2b_bills = json_payload.get("data", {}).get('data', {}).get("docdata", {})
            return_period = json_payload.get("data", {}).get('data', {}).get("rtnprd", {})
            for section_code, bill_datas in gstr2b_bills.items():
                if section_code in ('b2b', 'cdnr'):
                    for bill_by_vat in bill_datas:
                        key = section_code == 'cdnr' and 'nt' or 'inv'
                        for doc_data in bill_by_vat.get(key):
                            vals = {
                                'vat': bill_by_vat.get('ctin'),
                                'bill_number': section_code == 'cdnr' and doc_data.get('ntnum') or doc_data.get('inum'),
                                'bill_date': self.convert_to_date(doc_data.get('dt')),
                                'bill_total': doc_data.get('val'),
                                'bill_value_json': doc_data,
                                'bill_type': section_code == 'cdnr' and 'credit_note' or 'bill',
                                'section_code': section_code,
                            }
                            vals_list.append(vals)
                            if return_period != doc_data.get('supprd'):
                                late_vals_list.append(vals)
                if section_code == 'impg':
                    for bill_data in bill_datas:
                        vals_list.append({
                            'vat': False,
                            'bill_number': bill_data.get('boenum'),
                            'bill_date': self.convert_to_date(bill_data.get('boedt')),
                            'bill_taxable_value': bill_data.get('txval'),
                            'bill_value_json': bill_data,
                            'bill_type': 'bill',
                            'section_code': section_code,
                        })
                if section_code == 'impgsez':
                    for bill_by_vat in bill_datas:
                        for bill_data in bill_by_vat.get('boe'):
                            vals_list.append({
                                'vat': bill_by_vat.get('ctin'),
                                'bill_number': bill_data.get('boenum'),
                                'bill_date': self.convert_to_date(bill_data.get('boedt')),
                                'bill_taxable_value': bill_data.get('txval'),
                                'bill_value_json': bill_data,
                                'bill_type': 'bill',
                                'section_code': section_code,
                            })
            return vals_list, late_vals_list

        def process_json(json_dump_list):
            gstr2b_streamline_bills = []
            gstr2b_late_streamline_bills = []
            for json_dump in json_dump_list:
                json_payload = json.loads(json_dump)
                vals_list, late_vals_list = get_streamline_bills_from_json(json_payload)
                gstr2b_streamline_bills += vals_list
                gstr2b_late_streamline_bills += late_vals_list
            to_match_bills, matching_dict = _get_all_bill_by_matching_key(gstr2b_late_streamline_bills)
            checked_invoice = match_bills(gstr2b_streamline_bills, matching_dict)
            self.sudo().gstr2b_status = len(to_match_bills) == len(
                checked_invoice.filtered(lambda l: l.l10n_in_gstr2b_reconciliation_status in ('matched'))
            ) and 'fully_matched' or 'partially_matched'
            invoice_not_in_gstr2b = (to_match_bills - checked_invoice)
            invoice_not_in_gstr2b.write({
                'l10n_in_gstr2b_reconciliation_status': "bills_not_in_gstr2",
                'l10n_in_exception': "Not Available in GSTR2B",
                "l10n_in_gst_return_period_id": self.id,
            })

        json_payload_list = []
        for json_file in self.sudo().gstr2b_json_from_portal_ids:
            if json_file.mimetype == 'application/json':
                json_payload_list.append(json_file.raw)
        if json_payload_list:
            process_json(json_payload_list)
        else:
            self.sudo().write({
                "gstr2b_blocking_level": "error",
                "gstr2b_error": "Shomehow this GSTR2B attachment is not json",
            })

    # ===============================
    # GSTR-3B
    # ===============================

    def action_view_gstr3b_return_period(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("l10n_in_reports.action_l10n_in_gstr3b")
        action.update({
            'params': {
                'options': {
                    'date': {
                        'date_from': self.start_date.strftime('%Y-%m-%d'),
                        'date_to': self.end_date.strftime('%Y-%m-%d'),
                        'filter': 'custom',
                        'mode':'range',
                    },
                    'l10n_in_tax_unit': self.tax_unit_id.id,
                },
                'ignore_session': True,
            }
        })
        return action

    # ========================================
    # API calls
    # ========================================

    def _request(self, url, company, params=None):
        iap_service = self.env["iap.account"].get("l10n_in_edi")
        if not params:
            params = {}
        params.update(
            {
                "username": company.sudo().l10n_in_gstr_gst_username,
                "gstin": company.vat,
                "account_token": iap_service.account_token,
                'dbuuid': self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            }
        )
        default_endpoint = DEFAULT_IAP_ENDPOINT if company.sudo().l10n_in_gstr_gst_production_env else DEFAULT_IAP_TEST_ENDPOINT
        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_in_reports_gstr.endpoint", default_endpoint)
        url = "%s%s" % (endpoint, url)
        try:
            return jsonrpc(url=url, params=params, timeout=25)
        except AccessError as e:
            _logger.warning("Connection error: %s", e.args[0])
            return {
                "error": [{
                    "code": "404",
                    "message": _("Unable to connect to the GST service."
                        "The web service may be temporary down. Please try again in a moment.")
                }]
            }

    def _otp_request(self, company):
        return self._request(url="/iap/l10n_in_reports/1/authentication/otprequest", company=company)

    def _otp_auth_request(self, company, transaction, otp):
        params = {"auth_token": transaction, "otp": otp}
        return self._request(url="/iap/l10n_in_reports/1/authentication/authtoken", params=params, company=company)

    def _refresh_token_request(self, company):
        params = {"auth_token": company.sudo().l10n_in_gstr_gst_token}
        return self._request(
            url="/iap/l10n_in_reports/1/authentication/refreshtoken", params=params, company=company)

    def _send_gstr1(self, company, month_year, json_payload):
        params = {
            "ret_period": month_year,
            "auth_token": company.sudo().l10n_in_gstr_gst_token,
            "json_payload": json_payload,
        }
        return self._request(url="/iap/l10n_in_reports/1/gstr1/retsave", params=params, company=company)

    def _get_gstr_status(self, company, month_year, reference_id):
        params = {
            "ret_period": month_year,
            "auth_token": company.sudo().l10n_in_gstr_gst_token,
            "reference_id": reference_id,
        }
        return self._request(url="/iap/l10n_in_reports/1/retstatus", params=params, company=company)

    def _get_gstr2b_data(self, company, month_year, file_number=None):
        params = {
            "ret_period": month_year,
            "auth_token": company.sudo().l10n_in_gstr_gst_token,
            "file_number": file_number,
        }
        return self._request(url="/iap/l10n_in_reports/1/gstr2b/all", params=params, company=company)
