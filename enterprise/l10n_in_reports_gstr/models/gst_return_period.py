# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re
import markupsafe

from babel.dates import get_quarter_names
from datetime import date, datetime, timedelta
from dateutil import relativedelta
from itertools import groupby
from markupsafe import Markup

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError, RedirectWarning
from odoo.tools import date_utils, float_is_zero, get_lang, html_escape, SQL
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import format_date
from .irn_exception import IrnException

import logging

_logger = logging.getLogger(__name__)
TOLERANCE_AMOUNT = 1.0  # Default fallback tolerance amount for GSTR-2B matching if the system parameter is unset.


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
    display_tax_unit = fields.Boolean(compute="_compute_display_tax_unit")
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
        ("01", "Jan - Mar"),
        ("04", "Apr - Jun"),
        ("07", "Jul - Sep"),
        ("10", "Oct - Dec"),
        ], default=_default_quarterly)
    year = fields.Char(default=_default_year)

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
    gstr1_include_einvoice = fields.Boolean(
        string="E-Invoice in GSTR-1",
        help="Enable this option to include invoice with generated E-invoices being pushing to GSTR-1.",
        tracking=True
    )

    # ===============================
    # GSTR-2B
    # ===============================

    gstr2b_status = fields.Selection(selection=[
        ('not_recived', 'Not Recived'),
        ('waiting_reception', 'Waiting Reception'),
        ('being_processed', 'Being Processed'),
        ('partially_matched', 'Partially Matched'),
        ('fully_matched', 'Matched'),
    ], default="not_recived", string="GSTR-2B Status", readonly=True, tracking=True)
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
    # Bill using IRN
    # ===============================

    irn_status = fields.Selection(selection=[
        ('to_download', 'To Download'),
        ('to_process', 'To Process'),
        ('process_with_error', 'Process With Error')
    ], string="IRN Status", readonly=True, tracking=True)
    list_of_irn_json_attachment_ids = fields.Many2many('ir.attachment', 'irn_attachment_portal_json', string='JSON with list of IRNs')
    l10n_in_gstr_activate_einvoice_fetch = fields.Selection(related="company_id.l10n_in_gstr_activate_einvoice_fetch")

    # ===============================
    # GSTR Common Methods
    # ===============================

    _sql_constraints = [(
        'unique_period',
        'UNIQUE(company_id, month, year, quarter)',
        "Return period must be unique."
    )]

    def _get_base_account_domain(self):
        return [
            ('company_id', 'in', (self.company_ids or self.company_id).ids),
            ("date", ">=", self.start_date),
            ("date", "<=", self.end_date),
        ]

    def _get_default_account_move_domain(self, is_purchase=False):
        AccountMove = self.env['account.move']
        move_type = is_purchase and AccountMove.get_purchase_types(True) or AccountMove.get_sale_types(True)
        return self._get_base_account_domain() + [
            ('move_type', 'in', move_type),
            ("state", "=", "posted"),
        ]

    def _get_default_aml_domain(self, gst_tags):
        return self._get_base_account_domain() + [
            ('move_id.move_type', 'in', self.env['account.move'].get_invoice_types(True)),
            ("move_id.state", "=", "posted"),
            ("tax_tag_ids", "in", gst_tags),
        ]

    @api.constrains('tax_unit_id')
    def _check_tax_unit(self):
        for record in self:
            if record.tax_unit_id and record.tax_unit_id.main_company_id != record.company_id:
                raise ValidationError(_('GST Unit main company is different than this period company.'))

    @api.constrains('month', 'quarter', 'year')
    def _check_gstr_status(self):
        for record in self:
            if record.gstr1_status != 'to_send' or record.gstr2b_status != 'not_recived':
                raise UserError(_("You cannot change GST filing period after sending/receiving GSTR data"))

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
            if period.periodicity == "monthly" and period.start_date:
                period.name = format_date(self.env, period.start_date, date_format="MMM-yyyy")
            elif period.periodicity == "trimester" and period.start_date and period.end_date:
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
                raise UserError(_("To Create Return Period Periodicity should be Monthly or Quarterly"))
            record.periodicity = periodicity

    @api.depends('month', 'quarter', 'year')
    def _compute_period_dates(self):
        for record in self:
            if record.periodicity == "monthly" and record.month:
                period_start = fields.Date.context_today(self).replace(day=1, month=int(record.month), year=int(record.year))
                time_period = date_utils.get_month(period_start)
            elif record.periodicity == "trimester" and record.quarter:
                period_start = fields.Date.context_today(self).replace(day=1, month=int(record.quarter), year=int(record.year))
                time_period = date_utils.get_quarter(period_start)
            else:
                time_period = (False, False)
            record.start_date, record.end_date = time_period

    @api.depends('end_date')
    def _compute_rtn_period_month_year(self):
        for period in self:
            if period.end_date:
                period.return_period_month_year = period.end_date.strftime("%m%Y")
            else:
                period.return_period_month_year = False

    @api.depends('end_date', 'company_id')
    def _compute_gstr3b_closing_entry(self):
        for return_period in self:
            closing_journal_entry = self.env['account.move'].search([
                ('move_type', '=', 'entry'),
                ('company_id', '=', return_period.company_id.id),
                ('tax_closing_report_id', '!=', False),
                ('date', '=', return_period.end_date),
            ], limit=1)
            return_period.gstr3b_closing_entry = closing_journal_entry
            return_period.gstr3b_status = closing_journal_entry.state == 'posted' and 'filed' or 'not_filed'

    @api.depends('gstr3b_closing_entry', 'gstr3b_closing_entry.state')
    def _compute_gstr3b_status(self):
        for return_period in self:
            return_period.gstr3b_status = return_period.gstr3b_closing_entry.state == 'posted' and 'filed' or 'not_filed'

    @api.depends('company_id')
    def _compute_display_tax_unit(self):
        self.display_tax_unit = self.env['account.tax.unit'].search_count([], limit=1) > 0

    @api.model
    def _check_config(self, next_gst_action=False, company=False):
        company = company or self.company_id
        action = False
        button_name = msg = ""
        if not company.vat:
            raise UserError(_("Please set company GSTIN"))
        if not company.sudo().l10n_in_gstr_gst_username:
            msg = _("First setup GST user name and validate using OTP from configuration")
            button_name = _('Go to the configuration panel')
            action = self.env.ref('account.action_account_config').id
        if not company._is_l10n_in_gstr_token_valid():
            context = {
                'default_company_id': company.id,
                'dialog_size': 'medium',
                'active_id': self._context.get('active_id', self.id),
                'active_model': self._context.get('active_model', 'l10n_in.gst.return.period'),
                'next_gst_action': next_gst_action,
            } if next_gst_action else False
            form = self.env.ref("l10n_in_reports_gstr.view_get_otp_gstr_validate_send_otp")
            action = {
                'name': _('OTP Request'),
                'type': 'ir.actions.act_window',
                'res_model': 'l10n_in.gst.otp.validation',
                'views': [[form.id, 'form']],
                'target': 'new',
                'context': context,
            }
            msg = _("The NIC portal connection has expired. To re-initiate the connection, you can send an OTP request.")
            button_name = _('Re-Initiate')
        if msg and button_name and action:
            raise RedirectWarning(msg, action, button_name)

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
                    raise UserError(_("You cannot delete GST Return Period after sending/receiving GSTR data"))

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
        context = {'active_id': self.id, 'active_model': 'l10n_in.gst.return.period'}
        return {
            "name": _("GST Return Period"),
            "res_model": "l10n_in.gst.return.period",
            "view_mode": "form",
            "res_id": self.id,
            "type": "ir.actions.act_window",
            'context': context,
            "views": [[self.env.ref('l10n_in_reports_gstr.l10n_in_gst_return_period_form_view').id, "form"]],
        }

    def _get_error_lavel(self, error_codes):
        warning_codes = {
            "RTN_24",  # File Generation is in progress, please try after sometime.
            "404",  # Resource temporarily unavailable / not found
            "RET2B1017",  # GSTR-2B data for the selected period is not yet available. Please try after sometime.
        }
        return "warning" if warning_codes.intersection(error_codes) else "error"

    @api.model
    def _get_gst_return_period(self, company, create_if_not_found=False):
        """
        Retrieve or create the GST return period for a given company and date.

        :param company: The company for which the GST return period is to be retrieved or created.
        :param create_if_not_found: If `True`, a new GST return period will be created if not found.

        :returns: The GST return period record for the specified company and date.
        """
        def _search_or_create_gst_return_period(period_date):
            month = period_date.strftime('%m').zfill(2)
            year = period_date.strftime('%Y')
            GstReturnPeriod = self.env['l10n_in.gst.return.period']
            domain = [
                ('company_id', '=', company.id),
                ('month', '=', month),
                ('year', '=', year),
            ]
            return_period = GstReturnPeriod.search(domain)
            if create_if_not_found:
                tax_units = self.env['account.tax.unit'].search([('main_company_id', '=', company.id)], limit=1)
                if tax_units and return_period and not return_period.tax_unit_id:
                    raise UserError(f"GST return period already exists for {period_date.strftime('%b-%Y')}, but it's not associated with the relevant tax unit.")
            if create_if_not_found and not return_period:
                return_period = GstReturnPeriod.create({
                    'company_id': company.id,
                    'year': year,
                    'month': month,
                    'tax_unit_id': tax_units.id if create_if_not_found else False,
                })
            return return_period

        current_return_period_date = fields.Date.context_today(self)
        current_return_period = _search_or_create_gst_return_period(current_return_period_date)
        return current_return_period

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
                    }
                }
            }
        """
        tax_vals_map = {}
        gst_tags = {
            'igst': self.env.ref('l10n_in.tax_tag_igst'),
            'cgst': self.env.ref('l10n_in.tax_tag_cgst'),
            'sgst': self.env.ref('l10n_in.tax_tag_sgst'),
            'cess': self.env.ref('l10n_in.tax_tag_cess'),
        }
        journal_items = self.env['account.move.line'].search(domain)
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details_from_domain(domain=domain)
        self._cr.execute(tax_details_query, tax_details_params)
        tax_details = self._cr.dictfetchall()
        # Retrieve base lines and tax lines based on tax_details
        base_lines = self.env['account.move.line'].browse([tax['base_line_id'] for tax in tax_details])
        tax_lines = self.env['account.move.line'].browse([tax['tax_line_id'] for tax in tax_details])
        base_lines_map = {line.id: line for line in base_lines}
        tax_lines_map = {line.id: line for line in tax_lines}
        seen_lines = set()
        for tax_vals in tax_details:
            base_line = base_lines_map[tax_vals['base_line_id']]
            tax_line = tax_lines_map[tax_vals['tax_line_id']]
            seen_lines.add(base_line.id)
            seen_lines.add(tax_line.id)
            move_id = base_line.move_id
            tax_vals_map.setdefault(move_id, {}).setdefault(base_line, {
                'base_amount': tax_vals['base_amount'],
                'l10n_in_reverse_charge': False,
                'rate_by_tax_tag': {},
                'gst_tax_rate': 0.00,
                'igst': 0.00,
                'cgst': 0.00,
                'sgst': 0.00,
                'cess': 0.00,
            })
            for tax_type, tag_id in gst_tags.items():
                if tag_id in tax_line.tax_tag_ids:
                    tax_vals_map[move_id][base_line][tax_type] += tax_vals['tax_amount']
                    if tax_type in ['igst', 'cgst', 'sgst']:
                        tax_vals_map[move_id][base_line]['rate_by_tax_tag'][tax_type] = tax_line.tax_line_id.amount
                    if tax_line.tax_line_id.l10n_in_reverse_charge:
                        tax_vals_map[move_id][base_line]['l10n_in_reverse_charge'] = True
            tax_vals_map[move_id][base_line]['gst_tax_rate'] = sum(tax_vals_map[move_id][base_line]['rate_by_tax_tag'].values())
        # IF line have 0% tax or not have tax then we add it manually
        for journal_item in self.env['account.move.line'].browse(list(set(journal_items.ids) - seen_lines)):
            move_id = journal_item.move_id
            tax_vals_map.setdefault(move_id, {}).setdefault(journal_item, {
                'base_amount': journal_item.balance,
                'l10n_in_reverse_charge': False,
                'gst_tax_rate': 0.0,
                'igst': 0.00,
                'cgst': 0.00,
                'sgst': 0.00,
                'cess': 0.00,
            })
        return tax_vals_map

    def _get_hsn_new_schema_apply_date(self):
        # TODO: Remove this fallback once the government finalizes the official HSN schema date.
        fallback_value = date(2025, 5, 1)
        try:
            param_value = self.env['ir.config_parameter'].sudo().get_param('l10n_in_reports.hsn_new_schema_apply_date')
            return datetime.strptime(param_value, DF).date() if param_value else fallback_value
        except (ValueError, TypeError):
            return fallback_value

    def _get_gstr1_hsn_json(self, journal_items, tax_details_by_move):
        # TO OVERRIDE on Point of sale for get details by product
        """
            This method is return hsn json as below
            Here invoice lines are grouped by GST treatment type, product HSN code, product unit code and GST tax rate.
            {'data/hsn_b2b/hsn_b2c': [{
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
        hsn_new_schema_apply_date = self._get_hsn_new_schema_apply_date()
        if self.start_date < hsn_new_schema_apply_date:
            hsn_json = {'data': {}}
        else:
            hsn_json = {'hsn_b2b': {}, 'hsn_b2c': {}}
        for move_id in journal_items.mapped('move_id'):
            # We sum value of invoice and credit note
            # so we need positive value for invoice and nagative for credit note
            tax_details = tax_details_by_move.get(move_id, {})
            if 'data' in hsn_json:
                hsn_section = 'data'
            elif move_id.l10n_in_gst_treatment in {'regular', 'composition', 'deemed_export', 'uin_holders', 'special_economic_zone'}:
                hsn_section = 'hsn_b2b'
            else:
                hsn_section = 'hsn_b2c'
            for line, line_tax_details in tax_details.items():
                tax_rate = line_tax_details['gst_tax_rate']
                if tax_rate.is_integer():
                    tax_rate = int(tax_rate)
                uqc = uoms.browse(line.product_uom_id.id).l10n_in_code and uoms.browse(line.product_uom_id.id).l10n_in_code.split("-")[0] or "OTH"
                if line.product_id.type == 'service':
                    # If product is service then UQC is Not Applicable (NA)
                    uqc = "NA"
                group_key = "%s-%s-%s" %(
                    tax_rate, line.l10n_in_hsn_code, uqc)
                hsn_json[hsn_section].setdefault(group_key, {
                    "hsn_sc": self.env["account.edi.format"]._l10n_in_edi_extract_digits(line.l10n_in_hsn_code),
                    "uqc": uqc,
                    "rt": tax_rate,
                    "qty": 0.00, "txval": 0.00, "iamt": 0.00, "samt": 0.00, "camt": 0.00, "csamt": 0.00})
                hsn_data = hsn_json[hsn_section][group_key]
                if line.product_id.type != 'service':
                    if move_id.move_type in ('in_refund', 'out_refund'):
                        hsn_data['qty'] -= line.quantity
                    else:
                        hsn_data['qty'] += line.quantity
                hsn_data['txval'] += line_tax_details.get('base_amount', 0.00) * -1
                hsn_data['iamt'] += line_tax_details.get('igst', 0.00) * -1
                hsn_data['samt'] += line_tax_details.get('cgst', 0.00) * -1
                hsn_data['camt'] += line_tax_details.get('sgst', 0.00) * -1
                hsn_data['csamt'] += line_tax_details.get('cess', 0.00) * -1
        return hsn_json

    def _get_doc_issue_json(self):
        # to overwrite in l10n_in_reports_gstr_document_summary
        return {
            'doc_det': []
        }

    def _get_gstr1_json(self):
        def _group_aml(group_by_field, journal_items):
            values = {}
            journal_items = journal_items.sorted(lambda l: l.mapped(group_by_field))
            for groupby_key, grouped_items in groupby(journal_items, lambda l: l.mapped(group_by_field)):
                values.setdefault(groupby_key, AccountMoveLine)
                for grouped_item in grouped_items:
                    values[groupby_key] += grouped_item
            return values

        def is_einvoice_skippable(move_id):
            # Check if the skip e-invoice condition is met for a given move_id.
            return (
                not self.gstr1_include_einvoice and
                any(
                    doc.edi_format_id.code == 'in_einvoice_1_03' and doc.state in ['sent', 'cancelled']
                    for doc in move_id.edi_document_ids
                )
            )

        def _process_hsn_data(hsn_data):
            """Helper function to process HSN data with rounding."""
            return [
                {**hsn_dict, 'num': index, **{
                    key: AccountEdiFormat._l10n_in_round_value(hsn_dict.get(key, 0))
                    for key in ('txval', 'iamt', 'camt', 'samt', 'csamt', 'qty')
                }}
                for index, hsn_dict in enumerate(hsn_data.values(), start=1)
            ]

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
                    if is_einvoice_skippable(move_id):
                        continue
                    lines_json = {}
                    is_reverse_charge = False
                    is_igst_amount = False
                    tax_details = tax_details_by_move.get(move_id)
                    for line_tax_details in tax_details.values():
                        # Ignore the lines if invoice is not SEZ and GST taxes are not selected
                        if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not line_tax_details['gst_tax_rate']:
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
                if inv_json_list:
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
                        if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not line_tax_details['gst_tax_rate']:
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
                    if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not line_tax_details['gst_tax_rate']:
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
                    if is_einvoice_skippable(move_id):
                        continue
                    lines_json = {}
                    is_igst_amount = False
                    is_reverse_charge = False
                    tax_details = tax_details_by_move[move_id]
                    for line_tax_details in tax_details.values():
                        if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not line_tax_details['gst_tax_rate']:
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
                        is_out_refund = move_id.move_type == "out_refund"
                        sign = is_out_refund and 1 or -1
                        inv_json = {
                            "ntty": is_out_refund and "C" or "D",
                            "nt_num": move_id.name,
                            "nt_dt": move_id.invoice_date.strftime("%d-%m-%Y"),
                            "val": AccountEdiFormat._l10n_in_round_value(move_id.amount_total_in_currency_signed * -sign),
                            "pos": move_id.l10n_in_state_id.l10n_in_tin,
                            "rchrg": is_reverse_charge and "Y" or "N",
                            "inv_typ": invoice_type,
                            "itms": [
                                {"num": index, "itm_det": {
                                    **line_json,
                                    "txval": AccountEdiFormat._l10n_in_round_value(line_json['txval'] * sign),
                                    "iamt": AccountEdiFormat._l10n_in_round_value(line_json['iamt'] * sign),
                                    "samt": AccountEdiFormat._l10n_in_round_value(line_json['samt'] * sign),
                                    "camt": AccountEdiFormat._l10n_in_round_value(line_json['camt'] * sign),
                                    "csamt": AccountEdiFormat._l10n_in_round_value(line_json['csamt'] * sign),
                                }} for index, line_json in enumerate(lines_json.values(), start=1)
                            ],
                        }
                        inv_json_list.append(inv_json)
                if inv_json_list:
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
                for line_tax_details in tax_details.values():
                    if move_id.l10n_in_gst_treatment != 'special_economic_zone' and not line_tax_details['gst_tax_rate']:
                        continue
                    if line_tax_details['igst']:
                        is_igst_amount = True
                    tax_rate = line_tax_details['gst_tax_rate']
                    lines_json.setdefault(tax_rate, {
                        "rt": tax_rate, "txval": 0.00, "iamt": 0.00, "csamt": 0.00})
                    lines_json[tax_rate]['txval'] += line_tax_details['base_amount']
                    lines_json[tax_rate]['iamt'] += line_tax_details['igst']
                    lines_json[tax_rate]['csamt'] += line_tax_details['cess']
                if lines_json:
                    invoice_type = 'B2CL'
                    is_out_refund = move_id.move_type == "out_refund"
                    sign = is_out_refund and 1 or -1
                    invoice_total = move_id.amount_total_signed * -sign
                    if move_id.l10n_in_gst_treatment == "overseas" and is_igst_amount:
                        invoice_type = 'EXPWP'
                        # If Base amount and Invoice total is same then add tax values in total for Export with payment only
                        if float_is_zero(invoice_total - sum(line['txval'] for line in lines_json.values()), precision_digits=2):
                            invoice_total += sum(line['iamt'] + line['csamt'] for line in lines_json.values())
                    elif move_id.l10n_in_gst_treatment == "overseas":
                        invoice_type = 'EXPWOP'
                    inv_json = {
                        "ntty": is_out_refund and "C" or "D",
                        "nt_num": move_id.name,
                        "nt_dt": move_id.invoice_date.strftime("%d-%m-%Y"),
                        "val": AccountEdiFormat._l10n_in_round_value(invoice_total),
                        "typ": invoice_type,
                        "itms": [
                            {"num": index, "itm_det": {
                                **line_json,
                                "txval": AccountEdiFormat._l10n_in_round_value(line_json['txval'] * sign),
                                "iamt": AccountEdiFormat._l10n_in_round_value(line_json['iamt'] * sign),
                                "csamt": AccountEdiFormat._l10n_in_round_value(line_json['csamt'] * sign),
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
                if is_einvoice_skippable(move_id):
                    continue
                tax_details = tax_details_by_move.get(move_id)
                lines_json = {}
                is_igst_amount = False
                for line_tax_details in tax_details.values():
                    if line_tax_details['igst']:
                        is_igst_amount = True
                    elif line_tax_details['sgst'] or line_tax_details['cgst']:
                        continue
                    tax_rate = line_tax_details['gst_tax_rate']
                    lines_json.setdefault(tax_rate, {"rt": tax_rate, "txval": 0.00, "iamt": 0.00, "csamt": 0.00})
                    lines_json[tax_rate]['txval'] += line_tax_details['base_amount'] * -1
                    lines_json[tax_rate]['iamt'] += line_tax_details['igst'] * -1
                    lines_json[tax_rate]['csamt'] += line_tax_details['cess'] * -1
                if lines_json:
                    invoice_total = move_id.amount_total_signed
                    invoice_type = 'WOPAY'
                    if is_igst_amount:
                        invoice_type = 'WPAY'
                        # If Base amount and Invoice total is same then add tax values in total for Export with payment only
                        if float_is_zero(invoice_total - sum(line['txval'] for line in lines_json.values()), precision_digits=2):
                            invoice_total += sum(line['iamt'] + line['csamt'] for line in lines_json.values())
                    export_json.setdefault(invoice_type, [])
                    export_inv = {
                        "inum": move_id.name,
                        "idt": move_id.invoice_date.strftime("%d-%m-%Y"),
                        "val": AccountEdiFormat._l10n_in_round_value(invoice_total),
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
            tags_id = self._get_l10n_in_taxes_tags_id_by_name()
            for move_id in journal_items.mapped('move_id'):
                if is_einvoice_skippable(move_id):
                    continue
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
                    base_line_tag_ids = line.tax_tag_ids.ids
                    if tags_id['nil_rated'] in base_line_tag_ids:
                        nil_json[supply_type]['nil_amt'] += line_tax_detail['base_amount'] * -1
                    if tags_id['exempt'] in base_line_tag_ids:
                        nil_json[supply_type]['expt_amt'] += line_tax_detail['base_amount'] * -1
                    if tags_id['non_gst_supplies'] in base_line_tag_ids:
                        nil_json[supply_type]['ngsup_amt'] += line_tax_detail['base_amount'] * -1
            return nil_json and {'inv': list({
                **d,
                "nil_amt": AccountEdiFormat._l10n_in_round_value(d['nil_amt']),
                "expt_amt": AccountEdiFormat._l10n_in_round_value(d['expt_amt']),
                "ngsup_amt": AccountEdiFormat._l10n_in_round_value(d['ngsup_amt']),
            } for d in nil_json.values())} or {}

        def _get_supeco_clttx_json(journal_items):
            """
            contains supeco details for section 52
            This method is return clttx list as below
            Here data is grouped by etin(reseller_partner_gstin) and sum of base and gst taxes (TCS 1%)
            [{
                    "etin": "20ALYPD6528PQC5",
                    "suppval": 10000,
                    "igst": 1000,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0,
            }]
            """
            clttx_json = {}
            for move_id in journal_items.mapped('move_id'):
                tax_details = tax_details_by_move.get(move_id)
                eco_gstin = move_id.l10n_in_reseller_partner_id.vat
                for line_tax in tax_details.values():
                    clttx_json.setdefault(eco_gstin, {
                        "etin": eco_gstin,
                        "suppval": 0.00,
                        "igst": 0.00,
                        "sgst": 0.00,
                        "cgst": 0.00,
                        "cess": 0.00,
                    })
                    clttx_json[eco_gstin]['suppval'] += line_tax['base_amount'] * -1
                    clttx_json[eco_gstin]['cgst'] += line_tax['cgst'] * -1
                    clttx_json[eco_gstin]['sgst'] += line_tax['sgst'] * -1
                    clttx_json[eco_gstin]['igst'] += line_tax['igst'] * -1
                    clttx_json[eco_gstin]['cess'] += line_tax['cess'] * -1
            return [{
                **d,
                "suppval": AccountEdiFormat._l10n_in_round_value(d['suppval']),
                "igst": AccountEdiFormat._l10n_in_round_value(d['igst']),
                "cgst": AccountEdiFormat._l10n_in_round_value(d['cgst']),
                "sgst": AccountEdiFormat._l10n_in_round_value(d['sgst']),
                "cess": AccountEdiFormat._l10n_in_round_value(d['cess']),
            } for d in clttx_json.values()]

        def _get_supeco_paytx_json(journal_items):
            """
            contains supeco details for section 9(5)
            This method is return paytx list as below
            Here data is grouped by etin(reseller_partner_gstin)
            [{
                "etin": "20ALYPD6528PQC5",
                "suppval": 10000,
                "igst": 1000,
                "cgst": 0,
                "sgst": 0,
                "cess": 0,
            }]
            """
            paytx_json = {}
            for move_id in journal_items.mapped('move_id'):
                tax_details = tax_details_by_move.get(move_id)
                eco_gstin = move_id.l10n_in_reseller_partner_id.vat
                for line_tax_details in tax_details.values():
                    paytx_json.setdefault(eco_gstin, {
                        "etin": eco_gstin,
                        "suppval": 0.00,
                        "igst": 0.00,
                        "sgst": 0.00,
                        "cgst": 0.00,
                        "cess": 0.00,
                    })
                    paytx_json[eco_gstin]['suppval'] += line_tax_details['base_amount'] * -1
                    paytx_json[eco_gstin]['igst'] += line_tax_details['igst'] * -1
                    paytx_json[eco_gstin]['cgst'] += line_tax_details['cgst'] * -1
                    paytx_json[eco_gstin]['sgst'] += line_tax_details['sgst'] * -1
                    paytx_json[eco_gstin]['cess'] += line_tax_details['cess'] * -1

            return [{
                **d,
                "suppval": AccountEdiFormat._l10n_in_round_value(d['suppval']),
                "igst": AccountEdiFormat._l10n_in_round_value(d['igst']),
                "cgst": AccountEdiFormat._l10n_in_round_value(d['cgst']),
                "sgst": AccountEdiFormat._l10n_in_round_value(d['sgst']),
                "cess": AccountEdiFormat._l10n_in_round_value(d['cess']),
            } for d in paytx_json.values()]

        AccountMoveLine = self.env['account.move.line'].sudo()
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
            'exp': _get_exp_json(AccountMoveLine.search(self._get_section_domain('exp'))),
            'doc_issue': self._get_doc_issue_json()
            # Indian Government is not supporting supeco in the production
            # 'supeco': {
            #     'clttx': _get_supeco_clttx_json(AccountMoveLine.search(self._get_section_domain('supeco_clttx'))), # details for section 52 (TCS)
            #     'paytx': _get_supeco_paytx_json(AccountMoveLine.search(self._get_section_domain('supeco_paytx'))) #details for section 9(5)
            # }
        }
        if nil_json:
            return_json.update({'nil': nil_json})
        if hsn_json:
            return_json['hsn'] = {
                hsn_section: _process_hsn_data(hsn_json[hsn_section])
                for hsn_section in hsn_json
            }
        return return_json

    def button_send_gstr1(self):
        cron = self.env.ref('l10n_in_reports_gstr.ir_cron_to_send_gstr1_data')
        cron_sudo = cron.sudo()
        if not cron_sudo.active:
            if self.env.user.has_group('base.group_system'):
                message = _("Can not send GSTR-1 data because the required scheduled action '%s' is not active.", cron_sudo.cron_name)
                action = {
                    'name': _("Scheduled Action"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'ir.cron',
                    'res_id': cron.id,
                    'views': [[False, 'form']],
                }
                raise RedirectWarning(message, action, _("Go to Scheduled Action"))
            else:
                raise ValidationError(_("Can not send GSTR-1 data because the required scheduled action '%s' is not active.\nPlease contact your system administrator.", cron_sudo.cron_name))

        self._check_config(next_gst_action='send_gstr1')
        if not self.env['account.move.line'].sudo().search_count(self._get_section_domain('hsn'), limit=1):
            raise ValidationError(_("There are no transactions available for the current period to send for GSTR-1 filing."))

        # TODO remove in master
        # If the periodicity is `trimester`, the return_period_month_year is computed based on the start month of the period.
        # But it should be `end month of the period + year`. ex. 032025, 062025, etc.
        # Therefore, the compute needs to be triggered manually for existing records.
        if self.periodicity == 'trimester':
            self._compute_rtn_period_month_year()

        self.sudo().write({
            "gstr1_error": False,
            "gstr1_blocking_level": False,
            "gstr1_status": "sending",
        })
        cron._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': _("Action triggered — now waiting in queue to prepare and send data."),
                'sticky': True,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            }
        }

    def _cron_send_gstr1_data(self, job_count=None):
        gstr1_sending = self.search([("gstr1_status", "=", "sending"), ("gstr1_blocking_level", "!=", "error")])
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
        if not self.company_id._is_l10n_in_gstr_token_valid():
            self.sudo().write({
                "gstr1_blocking_level": "error",
                "gstr1_error": _("GSTR-1 submission failed:  GST token expired or missing, Please regenerate it by verifying GST OTP."),
            })
            return
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
                "gstr1_error": _(
                    "Something is wrong in response. Please contact support.\n response: %(response)s",
                    response=response
                ),
            })

    def button_check_gstr1_status(self):
        self.ensure_one()
        if self.gstr1_status != "waiting_for_status":
            raise AccessError(_("TO check status please push the GSTN"))
        self._check_config(next_gst_action='gstr1_status')
        self.check_gstr1_status()

    def _get_gstr_responsible_activity_and_user(self):
        """
        Retrieve the mail activity type for GSTR-1 exceptions and identify the responsible user.
        """
        act_type_xmlid = 'l10n_in_reports_gstr.mail_activity_type_gstr1_exception_to_be_sent'
        act_type = self.env.ref(act_type_xmlid, raise_if_not_found=False)
        # Ensure the activity type exists; create if missing
        if not act_type:
            act_type = self.env['mail.activity.type'].sudo()._load_records([{
                'xml_id': act_type_xmlid,
                'noupdate': False,
                'values': {
                    'name': 'GSTR-1 Exception',
                    'summary': 'GSTR-1 exception sent to the responsible user of the journal entry',
                    'category': 'default',
                    'delay_count': 0,
                    'delay_unit': 'days',
                    'delay_from': 'current_date',
                    'res_model': 'account.move',
                    'chaining_type': 'suggest',
                }
            }])

        # Determine the responsible user
        advisor_user = self.env['res.users']
        company_ids = self.company_ids or self.company_id
        if (
            act_type.default_user_id and
            act_type.default_user_id.has_group(self.env.ref('account.group_account_manager').id) and
            any(company in act_type.default_user_id.company_ids for company in company_ids)
        ):
            advisor_user = act_type.default_user_id
        else:
            field_id = self.env['ir.model.fields']._get('l10n_in.gst.return.period', 'gstr1_status')
            # Search for the last relevant mail message to find a responsible user
            last_message = self.env['mail.message'].search([
                ('model', '=', self._name),
                ('res_id', '=', self.id),
                ('create_uid', '!=', SUPERUSER_ID),
                ('create_uid.groups_id', 'in', self.env.ref('account.group_account_manager').ids),
                ('tracking_value_ids.field_id', '=', field_id.id),
            ], limit=1)
            advisor_user = last_message and last_message.create_uid or self.env.user

        return act_type_xmlid, advisor_user

    def check_gstr1_status(self):
        if not self.company_id._is_l10n_in_gstr_token_valid():
            self.sudo().write({
                "gstr1_blocking_level": "error",
                "gstr1_error": _("GSTR-1 check status failed: GST token expired or missing, Please regenerate it by verifying GST OTP."),
            })
            return
        response = self._get_gstr_status(
            company=self.company_id, month_year=self.return_period_month_year, reference_id=self.gstr_reference)
        if response.get('data'):
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
                    "gstr1_error": _("Waiting for GSTR-1 processing, try in a few minutes"),
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
                    message = "[%s] %s" % (error_report.get('error_cd'), error_report.get('error_msg'))
                else:
                    act_type_xmlid, advisor_user = self._get_gstr_responsible_activity_and_user()
                    error_report_summary = {}
                    for section_code, invoices in data.get('error_report', {}).items():
                        error_report_summary[section_code] = {}
                        for invoice in invoices:
                            error_code = invoice.get('error_cd', False)
                            error_message = invoice.get('error_msg', False)
                            invoice_number = None
                            if error_code or error_message:
                                # Extract invoice number based on section_code type
                                if section_code in ('b2b', 'b2cl', 'exp'):
                                    invoice_number = invoice.get('inv')[0].get('inum')
                                if section_code == "cdnr":
                                    invoice_number = invoice.get('nt')[0].get('nt_num')
                                if section_code == 'cdnur':
                                    invoice_number = invoice.get('nt_num')
                            # Search for the corresponding account move
                            move = (
                                AccountMove.search([
                                    ('name', '=', invoice_number),
                                    ('company_id', 'in', self.company_ids.ids or self.company_id.ids)
                                ], limit=1) if invoice_number else AccountMove
                            )
                            # Initialize section_code and move in the error report summary
                            error_report_summary[section_code].setdefault(move, {
                                "move_name": invoice_number,
                                "errors": {}
                            })
                            # Add error details to the corresponding move
                            error_report_summary[section_code][move]["errors"].update({error_code: error_message})
                    # Generate error messages and schedule activities
                    for section_code, moves in error_report_summary.items():
                        message += Markup("<li><b>%s :- </b></li>") % section_code.upper()
                        for move, move_details in moves.items():
                            error_note = Markup().join(Markup("<ul><li>%s - %s</li></ul>") % (error_code, error_message) for error_code, error_message in move_details["errors"].items())
                            if move:
                                # Generate a clickable link for the invoice
                                message += Markup(
                                    "<ul><li>Invoice : <a href='#' data-oe-model='account.move' data-oe-id='%s'>%s</a></li>%s</ul>"
                                ) % (move.id, move.name, error_note)
                                move.activity_schedule(
                                    act_type_xmlid=act_type_xmlid,
                                    user_id=advisor_user.id,
                                    note=_('GSTR-1 Processed with Error: %s', error_note)
                                )
                            else:
                                message += error_note
                # Create message in Return period
                self.sudo().message_post(
                    subject=_("GSTR-1 Errors"),
                    body=_('%s', message),
                    attachments=[("status_response.json", json.dumps(response))])
            else:
                self.sudo().write({
                    "gstr1_blocking_level": "error",
                    "gstr1_error": _(
                        "Something is wrong in response. Please contact support. \n response: %(response)s",
                        response=response
                    ),
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
                "gstr1_error": _("Something is wrong in response. Please contact support"),
            })

    def _cron_check_gstr1_status(self):
        sent_rtn = self.search([("gstr1_status", "=", "waiting_for_status")])
        for rtn in sent_rtn:
            rtn.check_gstr1_status()

    def _get_l10n_in_taxes_tags_id_by_name(self, only_gst_tags=False):
        tags_name = ['sgst', 'cgst', 'igst', 'cess']
        if not only_gst_tags:
            tags_name += [f'base_{tax_name}' for tax_name in tags_name] + ['zero_rated', 'exempt', 'nil_rated', 'non_gst_supplies']
        return {
            tag_name: self.env['ir.model.data']._xmlid_to_res_id(f"l10n_in.tax_tag_{tag_name}")
            for tag_name in tags_name
        }

    def _get_section_domain(self, section_code):
        taxes_tag_ids = self._get_l10n_in_taxes_tags_id_by_name()
        sgst_tag_ids = [taxes_tag_ids['base_sgst'], taxes_tag_ids['sgst']]
        cgst_tag_ids = [taxes_tag_ids['base_cgst'], taxes_tag_ids['cgst']]
        igst_tag_ids = [taxes_tag_ids['base_igst'], taxes_tag_ids['igst']]
        cess_tag_ids = [taxes_tag_ids['base_cess'], taxes_tag_ids['cess']]
        gst_tags = sgst_tag_ids + cgst_tag_ids + igst_tag_ids + cess_tag_ids
        nil_tags = [taxes_tag_ids[key] for key in ['exempt', 'nil_rated', 'non_gst_supplies']]
        export_tags = igst_tag_ids + [taxes_tag_ids['zero_rated']] + cess_tag_ids + nil_tags
        gst_with_other_tags = gst_tags + [taxes_tag_ids['zero_rated']] + nil_tags
        domain = self._get_base_account_domain() + [
            ("move_id.state", "=", "posted"),
            ("display_type", "not in", ('rounding', 'line_note', 'line_section'))
        ]
        match section_code:
            case "b2b":
                return (
                    domain
                    + [
                        ("move_id.move_type", "in", ["out_invoice", "out_receipt"]),
                        ("move_id.debit_origin_id", "=", False),
                        '|', '&',
                        ("move_id.l10n_in_gst_treatment", "in", ("regular", "deemed_export", "uin_holders", "composition")),
                        ("tax_tag_ids", "in", gst_tags),
                        '&',
                        ("move_id.l10n_in_gst_treatment", "=", "special_economic_zone"),
                        ("tax_tag_ids", "in", gst_with_other_tags),
                    ]
                )
            case "b2cl":
                return (
                    domain
                    + [
                        ("move_id.move_type", "in", ["out_invoice", "out_receipt"]),
                        ("move_id.debit_origin_id", "=", False),
                        ("move_id.l10n_in_gst_treatment", "in", ("unregistered", "consumer")),
                        ("move_id.l10n_in_state_id", "!=", self.company_id.state_id.id),
                        "|", "&",
                        ("date", "<", date(2024, 11, 1)),
                        ("move_id.amount_total", ">", 250000),
                        "&",
                        ("date", ">=", date(2024, 11, 1)),
                        ("move_id.amount_total", ">", 100000),
                        ("tax_tag_ids", "in", gst_tags),
                    ]
                )
            case "b2cs":
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
                        "|", "&",
                        ("date", "<", date(2024, 11, 1)),
                        ("move_id.amount_total", "<=", 250000),
                        "&",
                        ("date", ">=", date(2024, 11, 1)),
                        ("move_id.amount_total", "<=", 100000),
                    ]
                )
            case "cdnr":
                return (
                    domain
                    + [
                        "|",
                        ("move_id.move_type", "=", "out_refund"),
                        "&",
                        ("move_id.move_type", "=", "out_invoice"),
                        ("move_id.debit_origin_id", "!=", False),
                        '|', '&',
                        ("move_id.l10n_in_gst_treatment", "in", ("regular", "deemed_export", "uin_holders", "composition")),
                        ("tax_tag_ids", "in", gst_tags),
                        '&',
                        ("move_id.l10n_in_gst_treatment", "=", "special_economic_zone"),
                        ("tax_tag_ids", "in", gst_with_other_tags),
                    ]
                )
            case "cdnur":
                return (
                    domain
                    + [
                        "|",
                        ("move_id.move_type", "=", "out_refund"),
                        "&",
                        ("move_id.move_type", "=", "out_invoice"),
                        ("move_id.debit_origin_id", "!=", False),
                        "|", "&",
                        ("move_id.l10n_in_gst_treatment", "=", "overseas"),
                        ("tax_tag_ids", "in", export_tags),
                        "&", "&", "&",
                        ("tax_tag_ids", "in", gst_tags),
                        ("move_id.l10n_in_gst_treatment", "in", ["unregistered", "consumer"]),
                        ("move_id.l10n_in_transaction_type", "=", "inter_state"),
                        "|", "&",
                        ("date", "<", date(2024, 11, 1)),
                        ("move_id.amount_total", ">", 250000),
                        "&",
                        ("date", ">=", date(2024, 11, 1)),
                        ("move_id.amount_total", ">", 100000),
                    ]
                )
            case "exp":
                return (
                    domain
                    + [
                        ("move_id.move_type", "in", ["out_invoice", "out_receipt"]),
                        ("move_id.debit_origin_id", "=", False),
                        ("move_id.l10n_in_gst_treatment", "=", "overseas"),
                        ("tax_tag_ids", "in", export_tags),
                    ]
                )
            case "nil":
                return (
                    domain
                    + [
                        ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                        ("move_id.l10n_in_gst_treatment", "not in", ["overseas", "special_economic_zone"]),
                        ("tax_tag_ids", "in", nil_tags),
                    ]
                )
            case "hsn":
                return (
                    domain
                    + [
                        ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                        ("tax_tag_ids", "in", gst_with_other_tags),
                    ]
                )
            case 'supeco_clttx':
                return (
                    domain
                    + [
                        ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                        ("move_id.l10n_in_reseller_partner_id.vat", "!=", False),
                        ("move_id.l10n_in_reseller_partner_id.industry_id", "=", self.env.ref('l10n_in.eco_under_section_52').id),
                        ("tax_tag_ids", "in", gst_tags),
                    ]
                )
            case 'supeco_paytx':
                return (
                    domain
                    + [
                        ("move_id.move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                        ("move_id.l10n_in_reseller_partner_id.vat", "!=", False),
                        ("move_id.l10n_in_reseller_partner_id.industry_id", "=", self.env.ref('l10n_in.eco_under_section_9_5').id),
                        ("tax_tag_ids", "in", gst_tags),
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
            "view_mode": "list,form",
        }

    def action_get_gstr2b_data(self):
        self._check_config(next_gst_action='fetch_gstr2b')

        # TODO remove in master
        # If the periodicity is `trimester`, the return_period_month_year is computed based on the start month of the period.
        # But it should be `end month of the period + year`. ex. 032025, 062025, etc.
        # Therefore, the compute needs to be triggered manually for existing records.
        if self.periodicity == 'trimester':
            self._compute_rtn_period_month_year()

        self.sudo().write({
            "gstr2b_status": "waiting_reception",
            "gstr2b_error": False,
            "gstr2b_blocking_level": False,
        })
        self.env.ref('l10n_in_reports_gstr.ir_cron_auto_sync_gstr2b_data')._trigger()

    def get_gstr2b_data(self):
        if not self.company_id._is_l10n_in_gstr_token_valid():
            self.sudo().write({
                "gstr2b_blocking_level": "error",
                "gstr2b_error": _("GSTR-2B data fetching failed: GST token expired or missing, Please regenerate it by verifying GST OTP."),
            })
            return
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
        for return_period in self.search([('gstr2b_status', '=', 'waiting_reception'), ('gstr2b_blocking_level', '!=', 'error')]):
            return_period.get_gstr2b_data()

    def convert_to_date(self, date):
        # can't use field.date.to_date because formate is different then DEFAULT_SERVER_DATE_FORMAT
        return datetime.strptime(date, "%d-%m-%Y").date()

    def _cron_gstr2b_match_data(self):
        return_periods = self.search([('gstr2b_status', '=', 'being_processed'), ('gstr2b_blocking_level', '!=', 'error')])
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

        def _remove_special_characters(ref):
            """Remove special characters from bill reference numbers."""
            if not ref:
                return ref
            pattern = re.compile(r'[^a-zA-Z0-9]')
            return pattern.sub('', ref)

        def _get_tolerance_amount():
            tolerance_value = self.env['ir.config_parameter'].sudo().get_param('l10n_in_reports_gstr.gstr2b_matching_tolerance_amount', TOLERANCE_AMOUNT)
            return float(tolerance_value)

        def remove_matched_bill_value(matching_dict, matching_keys_to_remove, matched_bill):
            for key in matching_keys_to_remove:
                # only remove matched bill
                if key in matching_dict:
                    matching_dict[key] -= matched_bill
                    # no value then delete key
                    if not matching_dict[key]:
                        del matching_dict[key]

        def match_bills(gstr2b_streamline_bills, matching_dict):
            create_vals = []
            checked_bills = self.env['account.move']
            try:
                tolerance_amount = _get_tolerance_amount()
            except ValueError:
                tolerance_amount = 0.009
            for gstr2b_bill in gstr2b_streamline_bills:
                amount = gstr2b_bill.get('bill_total')
                if gstr2b_bill.get('bill_taxable_value'):
                    amount = gstr2b_bill.get('bill_taxable_value')
                sanitized_ref = _remove_special_characters(gstr2b_bill.get('bill_number'))
                matching_keys = _get_matching_keys(
                    sanitized_ref, gstr2b_bill.get('vat'), gstr2b_bill.get('bill_date'),
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
                        remove_matched_bill_value(matching_dict, matching_keys, matched_bills)
                        exception = []
                        if matched_bills.ref == gstr2b_bill.get('bill_number'):
                            if 'bill_taxable_value' in gstr2b_bill and gstr2b_bill['bill_taxable_value'] != matched_bills.amount_untaxed:
                                exception.append(_("Total Taxable amount as per GSTR-2B is %s", gstr2b_bill['bill_taxable_value']))
                            amount_total = matched_bills.amount_total
                            sign = 1 if matched_bills.is_inbound(include_receipts=True) else -1
                            for line in matched_bills.line_ids:
                                if line.tax_line_id.amount < 0:
                                    amount_total += line.balance * sign
                            if 'bill_total' in gstr2b_bill and not (amount_total - tolerance_amount <= gstr2b_bill['bill_total'] <= amount_total + tolerance_amount):
                                exception.append(_("The total amount as per GSTR-2B is %s", gstr2b_bill['bill_total']))
                            if 'vat' in gstr2b_bill and gstr2b_bill['vat'] != matched_bills.partner_id.vat:
                                exception.append(_("The GSTIN as per GSTR-2B is %s", gstr2b_bill['vat']))
                            if 'bill_date' in gstr2b_bill and gstr2b_bill['bill_date'] != matched_bills.invoice_date:
                                exception.append(_("The bill date as per GSTR-2B is %s", gstr2b_bill['bill_date']))
                            if 'bill_type' in gstr2b_bill and (matched_bills.move_type == 'in_refund' and gstr2b_bill['bill_type'] == 'bill') or \
                                (matched_bills.move_type != 'in_refund' and gstr2b_bill['bill_type'] == 'credit_note'):
                                exception.append(_("The bill type as per GSTR-2B is %s", invoice_type))
                        elif (gstr2b_bill.get('bill_total') == matched_bills.amount_total or \
                            gstr2b_bill.get('bill_taxable_value') == matched_bills.amount_untaxed) and \
                            gstr2b_bill.get('vat') == matched_bills.partner_id.vat and \
                            gstr2b_bill.get('bill_date') == matched_bills.invoice_date and \
                            (matched_bills.move_type == 'in_refund' and gstr2b_bill.get('bill_type') == 'credit_note') or \
                            (matched_bills.move_type != 'in_refund' and gstr2b_bill.get('bill_type') == 'bill'):
                            exception.append(_("The reference number as per GSTR-2B is %s", gstr2b_bill['bill_number']))
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
                                body=_(
                                    "The reference number is the same as on other bills: %(other_bills)s",
                                    other_bills=other_bills
                                )
                            )
                        matched_bills.write({
                            "l10n_in_exception": _("We have found the same reference in other bills. For more details, please check the message in Chatter."),
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
                        *self.env['account.journal']._check_company_domain(self.company_ids or self.company_id),
                        ('type', '=', 'purchase')
                    ], order="sequence, id", limit=1)
                    default_l10n_in_gst_treatment = (gstr2b_bill.get('section_code') == 'impg' and 'overseas') or (gstr2b_bill.get('section_code') == 'impgsez' and 'special_economic_zone') or 'regular'
                    create_vals.append({
                        "move_type": gstr2b_bill.get('bill_type') == 'credit_note' and "in_refund" or "in_invoice",
                        "ref": gstr2b_bill.get('bill_number'),
                        "invoice_date": gstr2b_bill.get('bill_date'),
                        "partner_id": partner.id,
                        "l10n_in_gst_treatment": partner and partner.l10n_in_gst_treatment in ('deemed_export', 'uin_holders') and partner.l10n_in_gst_treatment or default_l10n_in_gst_treatment,
                        "journal_id": journal.id,
                        "l10n_in_gstr2b_reconciliation_status": "gstr2_bills_not_in_odoo",
                        "checked": False,
                        "l10n_in_gst_return_period_id": self.id,
                        "message_ids":[(0, 0, {
                            'model': 'account.move',
                            'body': _(
                                "This bill was created from the GSTR-2B reconciliation because "
                                "no existing bill matched with the given details."
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
                self._cr.execute(SQL("""
                    UPDATE ir_attachment
                    SET res_id = msg.res_id,
                        res_model = 'account.move'
                    FROM ir_attachment att
                    JOIN message_attachment_rel rel ON rel.attachment_id = att.id
                    JOIN mail_message msg ON msg.id = rel.message_id
                    WHERE att.id = ir_attachment.id
                        AND att.res_model IS NULL
                        AND att.res_id = 0
                        AND msg.model = 'account.move'
                        AND msg.res_id IN %(ids)s
                """, ids=tuple(created_move.ids)))
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
                bill_month_start, bill_month_end = date_utils.get_month(late_bill.get('bill_date'))
                to_match_bills += AccountMove.search([
                    ('l10n_in_gst_return_period_id', '!=', self.id),
                    ("invoice_date", ">=", bill_month_start),
                    ("invoice_date", "<=", bill_month_end),
                    ("company_id", "in", self.company_ids.ids or self.company_id.ids),
                    ("move_type", "in", AccountMove.get_purchase_types()),
                    ('ref', '=', late_bill.get('bill_number')),
                    ("state", "=", "posted"),
                    ("l10n_in_gst_treatment", "not in", ('composition', 'unregistered', 'consumer')),
                    ("l10n_in_gstr2b_reconciliation_status", "not in", ('matched', 'partially_matched')),
                ])
            filtered_to_match_bills = AccountMove
            for bill in to_match_bills:
                # There is no tax mins bill from unregistered and consumer so no need to match
                # If set this in domain then it will impact the performance because of tax_ids is m2m field, so put this condition here
                if bill.state == 'posted' and not bill.line_ids.tax_ids:
                    continue
                bill_type = 'bill'
                amount = bill.amount_total
                # For SEZ and overseas amount get from Goverment is amount_untaxed
                if bill.l10n_in_gst_treatment in ('special_economic_zone', 'overseas'):
                    amount = bill.amount_untaxed
                if bill.move_type == 'in_refund':
                    bill_type = 'credit_note'
                # Sanitize the reference to remove any special characters, ensuring it is suitable for matching
                sanitized_ref = _remove_special_characters(bill.ref)
                # Retrieve matching keys based on the sanitized reference, partner VAT, invoice date, bill type, and amount
                matching_keys = _get_matching_keys(sanitized_ref, bill.partner_id.vat, bill.invoice_date, bill_type, amount)
                for matching_key in matching_keys:
                    matching_dict.setdefault(matching_key, AccountMove)
                    matching_dict[matching_key] += bill
                filtered_to_match_bills += bill
            return filtered_to_match_bills, matching_dict

        def get_streamline_bills_from_json(json_payload):
            vals_list = []
            late_vals_list = []
            gstr2b_bills = json_payload.get("data", {}).get('data', {}).get("docdata", {})
            for section_code, bill_datas in gstr2b_bills.items():
                if section_code in ('b2b', 'cdnr'):
                    for bill_by_vat in bill_datas:
                        key = section_code == 'cdnr' and 'nt' or 'inv'
                        for doc_data in bill_by_vat.get(key):
                            bill_date = self.convert_to_date(doc_data.get('dt'))
                            vals = {
                                'vat': bill_by_vat.get('ctin'),
                                'bill_number': section_code == 'cdnr' and doc_data.get('ntnum') or doc_data.get('inum'),
                                'bill_date': bill_date,
                                'bill_total': doc_data.get('val'),
                                'bill_value_json': doc_data,
                                'bill_type': section_code == 'cdnr' and doc_data.get('typ') == 'C' and 'credit_note' or 'bill',
                                'section_code': section_code,
                            }
                            vals_list.append(vals)
                            if bill_date < self.start_date:
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
                "gstr2b_error": _("Somehow, the attached GSTR2B file is not in JSON format."),
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

    # ===============================
    # Bills from E-Invoice IRN
    # ===============================

    def action_get_irn_data(self):
        """
        Fetch the IRN (Invoice Reference Number) data for the company.
        Ensures the company is in production and has IAP credits, then triggers a cron to fetch
        the list of IRNs relevant to the current GST period.

        :returns: a notification action informing the user that the fetch is in progress.
        """
        if self.company_id.sudo().l10n_in_edi_production_env:
            edi_credits = self.env["iap.account"].get_credits(service_name="l10n_in_edi")
            if edi_credits < 3:
                url = self.env["iap.account"].get_credits_url(service_name="l10n_in_edi")
                self.irn_status = 'process_with_error'
                self.message_post(body=markupsafe.Markup("""
                    <p><b>%s</b></p><p>%s <a href="%s">%s</a></p>""") % (
                    _("You have insufficient credits to retrieve this document!"),
                    _("Please buy more credits and retry: "),
                    url,
                    _("Buy Credits")
                ))
                return True
        self._check_config(next_gst_action='fetch_irn')
        self.irn_status = 'to_download'
        self.message_post(body=_("IRN Processing is running in the background."))
        self.env.ref('l10n_in_reports_gstr.ir_cron_auto_sync_einvoice_irn')._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': _("Processing is running in the background. You can continue your work."),
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            }
        }

    def _get_irn_data(self):
        """ Fetch and process IRN data
        The process of retrieving IRN data entails the following steps:
        1. Obtain an e-invoice file token from the IAP.
        2. Use the token to retrieve the e-invoice file details, these include encryption keys and file URLs.
        3. Retrieve the IRN list file data from the encrypted file URLs, creates JSON attachments for each file. In most cases there is only one.
        4. Update the IRN status and trigger the next step in the workflow if successful.
        """
        def extract_token_from_error(response):
            """
            Extracts a file token from a specific error message if the error code matches.
            Handles specific errors and performs appropriate actions.
            :param response: The JSON response containing error details.
            :returns:
                - The extracted token as a string if `EINV30130` is found.
                - A dictionary with `error_code` if `EINV30109` is found (indicates retry).
                - `False` if no relevant error is found.
            """
            errors = response.get('error', [])
            if isinstance(errors, dict):
                errors['code'] = errors.pop('error_cd', None)
            for error in list(errors):
                error_code = error.get('code', '')
                # Handle `EINV30130`: Extract file token from the error message
                if error_code == 'EINV30130':
                    token_match = re.search(r'token\s([a-f0-9]+)(?=.*The link is valid till 1 day)', error.get('message', ''))
                    if token_match:
                        return token_match.group(1)
                # Handle `EINV30109`: File generation in progress, schedule a retry
                elif error_code == 'EINV30109':
                    # Dynamically activate and schedule a retry for the cron job after 10 minutes
                    self.env.ref("l10n_in_reports_gstr.ir_cron_auto_sync_einvoice_irn")._trigger(
                        fields.Datetime.now() + timedelta(minutes=10)
                    )
                    self.message_post(body=_("File generation is in progress on the GST portal. Auto retry in 10 minutes."))
                    return 'EINV30109_file_under_process'
            return False

        # Retrieve file token
        file_token_response = self._get_einvoice_file_token(
            company=self.company_id,
            month_year=self.return_period_month_year,
            section_code="B2B",
        )
        if (file_token := file_token_response.get('data', {}).get('token')) is None:
            file_token = extract_token_from_error(file_token_response)
        if file_token == 'EINV30109_file_under_process':
            return False
        if not file_token:
            raise IrnException(file_token_response.get('error', {}))
        # Retrieve encryption keys and URLs for the e-invoice files
        einvoice_details_response = self._get_einvoice_details_from_file(
            company=self.company_id,
            month_year=self.return_period_month_year,
            token=file_token,
        )
        if not (
            (data := einvoice_details_response.get('data', {}))
            and (url_list := [url['ul'] for url in data.get('urls') if 'ul' in url])
            and (key := data.get('ek'))
        ):
            raise IrnException(einvoice_details_response.get('error', {}))
        # Process the URLs to fetch IRN data and create attachments, exluding those that already exist
        attachment_ids = self.env['ir.attachment']
        for url in url_list:
            irn_details_response = self._get_encrypted_large_file_data(
                company=self.company_id,
                month_year=self.return_period_month_year,
                url=url,
                encryption_key=key,
            )
            data = irn_details_response.get('data', {})
            if not data or not data.get('irnList', {}):
                raise IrnException(irn_details_response.get('error', {}))
            attachment_ids |= self.env['ir.attachment'].create({
                'name': f'file_{url}.json',
                'mimetype': 'application/json',
                'raw': json.dumps(data),
            })
        if attachment_ids:
            self.list_of_irn_json_attachment_ids.unlink()
            self.list_of_irn_json_attachment_ids = attachment_ids
        # Update the IRN status and trigger the next workflow step
        self.irn_status = "to_process"
        self.env.ref('l10n_in_reports_gstr.ir_cron_auto_match_einvoice_irn')._trigger()

    def irn_match_data(self):
        """
        Matches or creates bills (account moves) based on IRN (Invoice Reference Number) data retrieved from JSON attachments.

        This method processes JSON data containing IRN information and attempts to match each entry with existing bills in the system.
        If a match is found, the IRN number is updated. If no match is found, a new bill is created.
        It handles updates, cancellations, and posting relevant messages based on the IRN status.
        """
        AccountMove = self.env['account.move']
        checked_moves = self.env['account.move']
        # Collect JSON data from the attachments
        json_payload_list = [
            json_file.raw
            for json_file in self.list_of_irn_json_attachment_ids
                if json_file.mimetype == 'application/json'
        ]

        if not json_payload_list:
            # No valid JSON attachments found, log an error
            self.irn_status = "process_with_error"
            msg = _("Somehow this IRN attachment is not JSON. Please attempt to retrieve the data from the portal again.")
            self.message_post(body=msg)
            return checked_moves

        # Process the JSON data
        irn_numbers = set()
        streamline_bills = []
        for json_dump in json_payload_list:
            json_payload = json.loads(json_dump)
            for entry in json_payload.get('irnList', {}):
                ctin = entry.get('ctin')
                irn_details = entry.get('irnDtl', [])
                for detail in irn_details:
                    vals = {
                        'vat': ctin,
                        'bill_number': detail.get('docNum'),
                        'bill_date': datetime.strptime(detail.get('docDt'), '%d/%m/%Y').strftime('%Y-%m-%d'),
                        'bill_total': detail.get('totInvAmt'),
                        'bill_value_json': detail,
                        'bill_type': detail.get('docType'),
                        'section_code': detail.get('supplyType'),
                        'irn_number': detail.get('irn'),
                        'irn_status': detail.get('irnStatus'),
                        'ack_no': detail.get('ackNo'),
                        'ack_date': detail.get('ackDt'),
                        'ewb_no': detail.get('ewbNo'),
                        'ewb_date': detail.get('ewbDt'),
                        'cancel_date': detail.get('cnldt')
                    }
                    streamline_bills.append(vals)
                    irn_numbers.add(detail.get('irn'))

        # Perform bulk search for bills with matching IRN numbers
        existing_bills = AccountMove.search([
            ("l10n_in_irn_number", "in", list(irn_numbers)),
            ("company_id", "in", self.company_ids.ids or self.company_id.ids)
        ])
        # Create a mapping of existing bills by IRN number
        existing_bills_dict = {bill.l10n_in_irn_number: bill for bill in existing_bills}

        # Match or create bills based on the extracted data
        for bill in streamline_bills:
            irn_number = bill.get('irn_number')
            bill_already_exists = existing_bills_dict.get(irn_number)
            if not bill_already_exists:
                # Check if the bill exists by bill number and date if IRN number does not match
                domain = [
                    ("move_type", "in", AccountMove.get_purchase_types()),
                    ("ref", "=", bill.get('bill_number')),
                    ("invoice_date", "=", bill.get('bill_date')),
                    ("company_id", "in", self.company_ids.ids or self.company_id.ids),
                ]
                if bill.get('vat'):
                    domain.append(("partner_id.vat", "=", bill.get('vat')))
                bill_already_exists = AccountMove.search(domain, limit=1)

                if bill_already_exists:
                    # Update the existing bill with the IRN number
                    bill_already_exists.l10n_in_irn_number = irn_number
                    msg = _("This bill was found in the GST portal while retrieving the list of IRNs.")
                    bill_already_exists.with_context(no_new_invoice=True).message_post(body=msg)

            if not bill_already_exists:
                # Create a new bill if no match is found
                journal = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(self.company_ids or self.company_id),
                    ('type', '=', 'purchase')
                ], order="sequence, id", limit=1)
                move_type = "in_invoice" if bill.get('bill_type') != "CRN" else "in_refund"
                created_move = self.env['account.move'].with_context(skip_is_manually_modified=True).create({
                    'journal_id': journal.id,
                    'move_type': move_type,
                    'l10n_in_irn_number': irn_number
                })

                if self.l10n_in_gstr_activate_einvoice_fetch == 'automatic':
                    try:
                        gov_json_data = created_move._l10n_in_retrieve_details_from_irn(irn_number, self.company_id)
                    except IrnException as e:
                        if str(e) == 'no-credit':
                            message = self.env['account.edi.format']._l10n_in_edi_get_iap_buy_credits_message()
                        else:
                            message = str(e)
                        created_move.message_post(body=Markup("%s<br/> %s") % (_("Fetching IRN details failed with error(s):"), message))
                        checked_moves |= created_move
                        continue
                    if gov_json_data:
                        # Create an attachment for the fetched data and update the bill
                        attachment = self.env['ir.attachment'].create({
                            # Limit the name to 45 characters to avoid exceeding the limit on e-invoice portal
                            'name': f'{irn_number[:45]}.json',
                            'mimetype': 'application/json',
                            'raw': json.dumps(gov_json_data),
                            'res_model': 'account.move',
                            'res_id': created_move.id,
                        })
                        created_move._extend_with_attachments(attachment, new=True)
                        msg = _("This bill was created from the GST portal because no existing invoice matched the provided details.")
                        created_move.with_context(account_predictive_bills_disable_prediction=True, no_new_invoice=True).message_post(body=msg)

                        # Cancel the created bill if the IRN status indicates cancellation
                        if bill.get('irn_status') == 'CNL' and created_move.state != 'cancel':
                            created_move.message_post(body=_("This bill has been marked as canceled based on the e-invoice status."))
                            created_move.button_cancel()

                if not (tools.config['test_enable'] or tools.config['test_file']):
                    self.env.cr.commit()
            else:
                # Cancel the existing bill if the IRN status indicates cancellation
                if bill.get('irn_status') == 'CNL' and bill_already_exists.state != 'cancel':
                    bill_already_exists.message_post(body=_("This bill has been marked as canceled based on the e-invoice status."))
                    bill_already_exists.button_cancel()

            checked_moves |= bill_already_exists or created_move

        # Post a final message with the number of processed bills
        msg = _("Fetching complete. %s bills have been matched or created.", len(checked_moves))
        self.message_post(body=msg)
        self.irn_status = False  # Reset IRN status after processing

    def _cron_get_irn_data(self):
        """
        Cron job to fetch IRN data for GST return periods with 'to_download' status.
        Calls `_get_irn_data()` for each period, handling errors if they occur.

        :rtype: None
        """
        return_periods = self.search([('irn_status', '=', 'to_download')])
        for return_period in return_periods:
            try:
                return_period._get_irn_data()
            except IrnException as e:
                if str(e) == 'no-credit':
                    message = self.env['account.edi.format']._l10n_in_edi_get_iap_buy_credits_message()
                else:
                    message = str(e)
                return_period.irn_status = 'process_with_error'
                return_period.message_post(body=Markup("%s<br/> %s") % (_("Fetching List of e-invoice..."), message))

    def _cron_irn_match_data(self):
        """
        Cron job method that matches IRN data for GST return periods with 'to_process' status.

        This method searches for all GST return periods marked for IRN data processing and
        calls the `irn_match_data` method on each applicable return period to perform the matching operation.

        :rtype: None
        """
        return_periods = self.search([('irn_status', '=', 'to_process')])
        for return_period in return_periods:
            return_period.irn_match_data()

    # ========================================
    # API calls
    # ========================================

    def _request(self, url, company, params=None):
        if not params:
            params = {}
        params.update({
            "username": company.sudo().l10n_in_gstr_gst_username,
            'gstin': company.vat,
        })
        try:
            return self.env['iap.account']._l10n_in_connect_to_server(
                company.sudo().l10n_in_edi_production_env,
                params,
                url,
                "l10n_in_reports_gstr.endpoint"
            )
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

    def _get_einvoice_file_token(self, company, month_year, section_code):
        """
        Retrieve the e-invoice file token for the specified return period and section code.

        :param company: The company for which the e-invoice file token is being retrieved.
        :param month_year: The return period in the format 'MM/YYYY'.
        :param section_code: The section code for the e-invoice.

        :returns: The response from the request containing the e-invoice file token.
        """
        params = {
            "ret_period": month_year,
            "suptyp": section_code,
            "gstin": company.vat,
            "auth_token": company.sudo().l10n_in_gstr_gst_token,
        }
        return self._request(url="/iap/l10n_in_reports/1/einvoice/vendor/irnlist", params=params, company=company)

    def _get_einvoice_details_from_file(self, company, month_year, token):
        """
        Get details of the e-invoice file using the provided file token.

        :param company: The company requesting the details.
        :param month_year: Return period ('MM/YYYY').
        :param token: E-invoice file token.

        :returns: E-invoice details response.
        """
        params = {
            "ret_period": month_year,
            "gstin": company.vat,
            "file_token": token,
            "auth_token": company.sudo().l10n_in_gstr_gst_token,
        }
        return self._request(url="/iap/l10n_in_reports/1/einvoice/filedtl", params=params, company=company)

    def _get_encrypted_large_file_data(self, company, month_year, url, encryption_key):
        """
        Retrieve data from an encrypted large file using its URL and encryption key.
        :returns: Decrypted file data response.
        """
        params = {
            "file_url": url,
            "encryption_key": encryption_key,
            "gstin": company.vat,
            "ret_period": month_year,
            "auth_token": company.sudo().l10n_in_gstr_gst_token,
        }
        return self._request(url="/iap/l10n_in_reports/1/all/largefile", params=params, company=company)
