# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenErp S.A. (<http://odoo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from xlwt import Workbook, easyxf
from openerp.exceptions import Warning
from datetime import timedelta, datetime
import calendar
import json
import lxml.html

class AccountReportFootnotesManager(models.TransientModel):
    _name = 'account.report.footnotes.manager'
    _description = 'manages footnotes'

    footnotes = fields.One2many('account.report.footnote', 'manager_id')

    @api.multi
    def add_footnote(self, type, target_id, column, number, text):
        self.env['account.report.footnote'].create(
            {'type': type, 'target_id': target_id, 'column': column, 'number': number, 'text': text, 'manager_id': self.id}
        )

    @api.multi
    def edit_footnote(self, number, text):
        footnote = self.footnotes.filtered(lambda s: s.number == number)
        footnote.write({'text': text})

    @api.multi
    def remove_footnote(self, number):
        footnotes = self.footnotes.filtered(lambda s: s.number == number)
        self.write({'footnotes': [(3, footnotes.id)]})


class AccountReportContextCommon(models.TransientModel):
    _name = "account.report.context.common"
    _description = "A particular context for a financial report"
    _inherits = {'account.report.footnotes.manager': 'footnotes_manager_id'}

    @api.model
    def get_context_by_report_name(self, name):
        report_match = json.loads(self.get_context_name_by_report_name())
        return self.env[report_match.get(name)]

    @api.model
    def get_context_name_by_report_name(self):
        return json.dumps({
            'financial_report': 'account.financial.report.context',
            'generic_tax_report': 'account.report.context.tax',
            'followup_report': 'account.report.context.followup',
            'bank_reconciliation': 'account.report.context.bank.reconciliation',
            'general_ledger': 'account.context.general.ledger',
            'l10n_be_partner_vat_listing': 'l10n.be.partner.vat.listing.context',
            })

    @api.model
    def get_context_name_by_report_model(self):
        return json.dumps({
            'account.financial.report': 'account.financial.report.context',
            'account.generic.tax.report': 'account.report.context.tax',
            'account.followup.report': 'account.report.context.followup',
            'account.bank.reconciliation.report': 'account.report.context.bank.reconciliation',
            'account.general.ledger': 'account.context.general.ledger',
            'l10n.be.report.partner.vat.listing': 'l10n.be.partner.vat.listing.context',
            })

    @api.model
    def get_full_report_name_by_report_name(self, name):
        if name == 'financial_report':
            return 'account.financial.report'
        if name == 'generic_tax_report':
            return 'account.generic.tax.report'
        if name == 'followup_report':
            return 'account.followup.report'
        if name == 'bank_reconciliation':
            return 'account.bank.reconciliation.report'
        if name == 'general_ledger':
            return 'account.general.ledger'
        if name == 'l10n_be_partner_vat_listing':
            return 'l10n.be.report.partner.vat.listing'

    def get_report_obj(self):
        raise Warning(_('get_report_obj not implemented'))

    @api.depends('create_uid')
    @api.one
    def _get_multi_company(self):
        group_multi_company = self.env['ir.model.data'].xmlid_to_object('base.group_multi_company')
        if self.create_uid.id in group_multi_company.users.ids:
            self.multi_company = True
        else:
            self.multi_company = False

    @api.depends('date_filter_cmp')
    @api.multi
    def _get_comparison(self):
        for context in self:
            if context.date_filter_cmp == 'no_comparison':
                context.comparison = False
            else:
                context.comparison = True

    date_from = fields.Date("Start date")
    date_to = fields.Date("End date")
    all_entries = fields.Boolean('Use all entries (not only posted ones)', default=False, required=True)
    multi_company = fields.Boolean('Allow multi-company', compute='_get_multi_company', store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda s: s.env.user.company_id)
    date_filter = fields.Char('Date filter used', default=None)
    next_footnote_number = fields.Integer(default=1, required=True)
    summary = fields.Char(default='')
    comparison = fields.Boolean(compute='_get_comparison', string='Enable comparison', default=False)
    date_from_cmp = fields.Date("Start date for comparison",
                                default=lambda s: datetime.today() + timedelta(days=-395))
    date_to_cmp = fields.Date("End date for comparison",
                              default=lambda s: datetime.today() + timedelta(days=-365))
    cash_basis = fields.Boolean('Enable cash basis columns', default=False)
    date_filter_cmp = fields.Char('Comparison date filter used', default='no_comparison')
    periods_number = fields.Integer('Number of periods', default=1)
    footnotes_manager_id = fields.Many2one('account.report.footnotes.manager', string='Footnotes Manager', required=True, ondelete='cascade')

    @api.multi
    def edit_summary(self, text):
        self.write({'summary': text})

    @api.multi
    def get_next_footnote_number(self):
        res = self.next_footnote_number
        self.write({'next_footnote_number': self.next_footnote_number + 1})
        return res

    @api.multi
    def set_next_number(self, num):
        self.write({'next_footnote_number': num})
        return

    @api.model
    def get_companies(self):
        return self.env['res.company'].search([])

    @api.multi
    def remove_line(self, line_id):
        raise Warning(_('remove_line not implemented'))

    @api.multi
    def add_line(self, line_id):
        raise Warning(_('add_line not implemented'))

    def get_columns_names(self):
        raise Warning(_('get_columns_names not implemented'))

    def get_full_date_names(self, dt_to, dt_from=None):
        dt_to = datetime.strptime(dt_to, "%Y-%m-%d")
        if dt_from:
            dt_from = datetime.strptime(dt_from, "%Y-%m-%d")
        if 'month' in self.date_filter:
            return dt_to.strftime('%b %Y')
        if 'quarter' in self.date_filter:
            quarter = (dt_to.month - 1) / 3 + 1
            return dt_to.strftime('Quarter #' + str(quarter) + ' %Y')
        if 'year' in self.date_filter:
            if self.company_id.fiscalyear_last_day == 31 and self.company_id.fiscalyear_last_month == 12:
                return dt_to.strftime('%Y')
            else:
                return str(dt_to.year - 1) + ' - ' + str(dt_to.year)
        if not dt_from:
            return dt_to.strftime('(as of %d %b %Y)')
        return dt_from.strftime('(From %d %b %Y <br />') + dt_to.strftime('to %d %b %Y)')

    def get_cmp_date(self):
        if self.get_report_obj().get_report_type() == 'no_date_range':
            return self.get_full_date_names(self.date_to_cmp)
        return self.get_full_date_names(self.date_to_cmp, self.date_from_cmp)

    def get_periods(self):
        res = self.get_cmp_periods()
        if self.get_report_obj().get_report_type() == 'no_date_range':
            res[:0] = [[False, self.date_to]]
        else:
            res[:0] = [[self.date_from, self.date_to]]
            if self.get_report_obj().get_report_type() == 'date_range_extended':
                dt_from = datetime.strptime(self.date_to, "%Y-%m-%d") + timedelta(days=1)
                res[:0] = [[dt_from.strftime("%Y-%m-%d"), False]]
                dt_to = datetime.strptime(res[-1][0], "%Y-%m-%d") - timedelta(days=1)
                res.append([False, dt_to.strftime("%Y-%m-%d")])
        return res

    def get_cmp_periods(self, display=False):
        if not self.comparison:
            return []
        dt_to = datetime.strptime(self.date_to, "%Y-%m-%d")
        if self.get_report_obj().get_report_type() != 'no_date_range':
            dt_from = datetime.strptime(self.date_from, "%Y-%m-%d")
        columns = []
        if self.date_filter_cmp == 'custom':
            if display:
                return ['Comparison<br />' + self.get_cmp_date(), '%']
            else:
                if self.get_report_obj().get_report_type() == 'no_date_range':
                    return [[False, self.date_to_cmp]]
                return [[self.date_from_cmp, self.date_to_cmp]]
        if self.date_filter_cmp == 'same_last_year':
            columns = []
            for k in xrange(0, self.periods_number):
                dt_to = dt_to.replace(year=dt_to.year - 1)
                if display:
                    if self.get_report_obj().get_report_type() == 'no_date_range':
                        columns += [self.get_full_date_names(dt_to.strftime("%Y-%m-%d"))]
                    else:
                        dt_from = dt_from.replace(year=dt_from.year - 1)
                        columns += [self.get_full_date_names(dt_to.strftime("%Y-%m-%d"), dt_from.strftime("%Y-%m-%d"))]
                else:
                    if self.get_report_obj().get_report_type() == 'no_date_range':
                        columns += [[False, dt_to.strftime("%Y-%m-%d")]]
                    else:
                        dt_from = dt_from.replace(year=dt_from.year - 1)
                        columns += [[dt_from.strftime("%Y-%m-%d"), dt_to.strftime("%Y-%m-%d")]]
            return columns
        if 'month' in self.date_filter:
            for k in xrange(0, self.periods_number):
                dt_to = dt_to.replace(day=1)
                dt_to -= timedelta(days=1)
                if display:
                    columns += [dt_to.strftime('%b %Y')]
                else:
                    if self.get_report_obj().get_report_type() == 'no_date_range':
                        columns += [[False, dt_to.strftime("%Y-%m-%d")]]
                    else:
                        dt_from -= timedelta(days=1)
                        dt_from = dt_from.replace(day=1)
                        columns += [[dt_from.strftime("%Y-%m-%d"), dt_to.strftime("%Y-%m-%d")]]
        elif 'quarter' in self.date_filter:
            quarter = (dt_to.month - 1) / 3 + 1
            year = dt_to.year
            for k in xrange(0, self.periods_number):
                if display:
                    if quarter == 1:
                        quarter = 4
                        year -= 1
                    else:
                        quarter -= 1
                    columns += ['Quarter #' + str(quarter) + ' ' + str(year)]
                else:
                    if dt_to.month == 12:
                        dt_to = dt_to.replace(month=9, day=30)
                    elif dt_to.month == 9:
                        dt_to = dt_to.replace(month=6, day=30)
                    elif dt_to.month == 6:
                        dt_to = dt_to.replace(month=3, day=31)
                    else:
                        dt_to = dt_to.replace(month=12, day=31, year=dt_to.year - 1)
                    if self.get_report_obj().get_report_type() == 'no_date_range':
                        columns += [[False, dt_to.strftime("%Y-%m-%d")]]
                    else:
                        if dt_from.month == 10:
                            dt_from = dt_from.replace(month=7)
                        elif dt_from.month == 7:
                            dt_from = dt_from.replace(month=4)
                        elif dt_from.month == 4:
                            dt_from = dt_from.replace(month=1)
                        else:
                            dt_from = dt_from.replace(month=10, year=dt_from.year - 1)
                        columns += [[dt_from.strftime("%Y-%m-%d"), dt_to.strftime("%Y-%m-%d")]]
        elif 'year' in self.date_filter:
            dt_to = datetime.strptime(self.date_to, "%Y-%m-%d")
            for k in xrange(0, self.periods_number):
                dt_to = dt_to.replace(year=dt_to.year - 1)
                if display:
                    if dt_to.strftime("%m-%d") == '12-31':
                        columns += [dt_to.year]
                    else:
                        columns += [str(dt_to.year - 1) + ' - ' + str(dt_to.year)]
                else:
                    if self.get_report_obj().get_report_type() == 'no_date_range':
                        columns += [[False, dt_to.strftime("%Y-%m-%d")]]
                    else:
                        dt_from = dt_to.replace(year=dt_to.year - 1) + timedelta(days=1)
                        columns += [[dt_from.strftime("%Y-%m-%d"), dt_to.strftime("%Y-%m-%d")]]
        else:
            if self.get_report_obj().get_report_type() != 'no_date_range':
                dt_from = datetime.strptime(self.date_from, "%Y-%m-%d")
                delta = dt_to - dt_from
                delta = timedelta(days=delta.days + 1)
                delta_days = delta.days
                for k in xrange(0, self.periods_number):
                    dt_from -= delta
                    dt_to -= delta
                    if display:
                        columns += [str((k + 1) * delta_days) + ' - ' + str((k + 2) * delta_days) + ' days ago']
                    else:
                        columns += [[dt_from.strftime("%Y-%m-%d"), dt_to.strftime("%Y-%m-%d")]]
            else:
                for k in xrange(0, self.periods_number):
                    dt_to -= timedelta(days=calendar.monthrange(dt_to.year, dt_to.month > 1 and dt_to.month - 1 or 12)[1])
                    if display:
                        columns += [dt_to.strftime('(as of %d %b %Y)')]
                    else:
                        columns += [[False, dt_to.strftime("%Y-%m-%d")]]
        return columns

    @api.model
    def create(self, vals):
        res = super(AccountReportContextCommon, self).create(vals)
        report_type = res.get_report_obj().get_report_type()
        if report_type in ['date_range', 'date_range_cash', 'no_comparison']:
            dt = datetime.today()
            update = {
                'date_from': datetime.today().replace(day=1),
                'date_to': dt.replace(day=calendar.monthrange(dt.year, dt.month)[1]),
                'date_filter': 'this_month',
            }
        elif report_type == 'date_range_extended':
            dt = datetime.today()
            update = {
                'date_from': datetime.today() - timedelta(days=29),
                'date_to': datetime.today(),
                'date_filter': 'custom',
                'date_filter_cmp': 'previous_period',
                'periods_number': 3,
            }
        else:
            update = {
                'date_from': datetime.today(),
                'date_to': datetime.today(),
                'date_filter': 'today',
            }
        res.write(update)
        return res

    def get_xml(self):
        return self.env['account.financial.report.xml.export'].do_xml_export(self)

    def get_pdf(self):
        report_obj = self.get_report_obj()
        lines = report_obj.with_context(print_mode=True).get_lines(self)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'context': self,
            'report': report_obj,
            'lines': lines,
            'mode': 'print',
            'base_url': base_url,
            'css': '',
            'o': self.env.user,
            'company': self.env.user.company_id,
            'res_company': self.env.user.company_id,
        }
        html = self.pool['ir.ui.view'].render(self._cr, self._uid, "account_reports.report_financial_letter", rcontext, context=self.env.context)

        header = self.pool['ir.ui.view'].render(self._cr, self._uid, "report.external_layout_header", rcontext, context=self.env.context)
        rcontext['body'] = header
        header = self.pool['ir.ui.view'].render(self._cr, self._uid, "report.minimal_layout", rcontext, context=self.env.context)
        footer = self.pool['ir.ui.view'].render(self._cr, self._uid, "report.external_layout_footer", rcontext, context=self.env.context)
        rcontext['body'] = footer
        rcontext['subst'] = True
        footer = self.pool['ir.ui.view'].render(self._cr, self._uid, "report.minimal_layout", rcontext, context=self.env.context)

        landscape = False
        if len(self.get_columns_names()) > 4:
            landscape = True

        return self.env['report']._run_wkhtmltopdf([header], [footer], [(0, html)], landscape, self.env.user.company_id.paperformat_id)

    def get_xls(self, response):
        book = Workbook()
        report_id = self.get_report_obj()
        sheet = book.add_sheet(report_id.get_title())

        title_style = easyxf('font: bold true; borders: bottom medium;')
        level_0_style = easyxf('font: bold true; borders: bottom medium, top medium; pattern: pattern solid;')
        level_0_style_left = easyxf('font: bold true; borders: bottom medium, top medium, left medium; pattern: pattern solid;')
        level_0_style_right = easyxf('font: bold true; borders: bottom medium, top medium, right medium; pattern: pattern solid;')
        level_1_style = easyxf('font: bold true; borders: bottom medium, top medium;')
        level_1_style_left = easyxf('font: bold true; borders: bottom medium, top medium, left medium;')
        level_1_style_right = easyxf('font: bold true; borders: bottom medium, top medium, right medium;')
        level_2_style = easyxf('font: bold true; borders: top medium;')
        level_2_style_left = easyxf('font: bold true; borders: top medium, left medium;')
        level_2_style_right = easyxf('font: bold true; borders: top medium, right medium;')
        level_3_style = easyxf()
        level_3_style_left = easyxf('borders: left medium;')
        level_3_style_right = easyxf('borders: right medium;')
        domain_style = easyxf('font: italic true;')
        domain_style_left = easyxf('font: italic true; borders: left medium;')
        domain_style_right = easyxf('font: italic true; borders: right medium;')
        upper_line_style = easyxf('borders: top medium;')
        def_style = easyxf()

        sheet.col(0).width = 10000

        sheet.write(0, 0, '', title_style)

        x = 1
        for column in self.get_columns_names():
            sheet.write(0, x, column, title_style)
            x += 1

        y_offset = 1
        lines = report_id.with_context(no_format=True, print_mode=True).get_lines(self)

        for y in range(0, len(lines)):
            if lines[y].get('level') == 0:
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1:
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[y].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            elif lines[y].get('type') != 'line':
                style_left = domain_style_left
                style_right = domain_style_right
                style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in xrange(1, len(lines[y]['columns']) + 1):
                if isinstance(lines[y]['columns'][x - 1], tuple):
                    lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(y + y_offset, x, lines[y]['columns'][x - 1], style)
                else:
                    sheet.write(y + y_offset, x, lines[y]['columns'][x - 1], style_right)
        for x in xrange(0, len(lines[0]['columns']) + 1):
            sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        book.save(response.stream)


class AccountReportFootnote(models.TransientModel):
    _name = "account.report.footnote"
    _description = "Footnote for reports"

    type = fields.Char()
    target_id = fields.Integer()
    column = fields.Integer()
    number = fields.Integer()
    text = fields.Char()
    manager_id = fields.Many2one('account.report.footnotes.manager')
