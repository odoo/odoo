# -*- coding: utf-8 -*-
#################################################################################
# Author : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import api, fields, models
import xlwt
import io
import base64
from odoo.tools.misc import formatLang, format_date


class AccountingReportWizard(models.TransientModel):
    _name = "accounting.report.profit.loss"
    _inherit = "account.common.report"
    _description = "Report Profit Loss"

    @api.model
    def _get_account_report(self):
        reports = []
        if self._context.get('active_id'):
            menu = self.env['ir.ui.menu'].browse(self._context.get('active_id')).name
            reports = self.env['account.financial.report'].search([('name', 'ilike', menu)])
        return reports and reports[0] or False

    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries')], string="Target Moves")
    enable_filter = fields.Boolean(string='Enable Comparison')
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    account_report_id = fields.Many2one('account.financial.report', string='Account Reports', required=True,
                                        default=_get_account_report)
    label_filter = fields.Char(string='Column Label',
                               help="This label will be displayed on report to show the balance computed for the given comparison filter.")
    filter_cmp = fields.Selection([('filter_no', 'No Filters'), ('filter_date', 'Date')], string='Filter by',
                                  required=True, default='filter_no')
    date_from_cmp = fields.Date(string='CMP Start Date')
    date_to_cmp = fields.Date(string='CMP End Date')
    debit_credit = fields.Boolean(string='Display Debit/Credit Columns',
                                  help="This option allows you to get more details about the way your balances are computed. Because it is space consuming, we do not allow to use it while doing a comparison.")
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], string="State", default='choose')
    name = fields.Char(string='File Name', readonly=True)
    data = fields.Binary(string="Data")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)

    def _build_comparison_context(self, data):
        result = {'journal_ids': 'journal_ids' in data['form'] and data['form']['journal_ids'] or False,
                  'state': 'target_move' in data['form'] and data['form']['target_move'] or ''}
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
            result['strict_range'] = True
        return result

    def check_report(self):
        res = super(AccountingReportWizard, self).check_report()
        data = {'form': self.read(
            ['account_report_id', 'date_from_cmp', 'date_to_cmp', 'journal_ids', 'filter_cmp', 'target_move'])[0]}
        for field in ['account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(data)
        res['data']['form']['comparison_context'] = comparison_context
        return res

    def _print_report(self, data):
        data['form'].update(self.read(
            ['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp', 'account_report_id', 'enable_filter',
             'label_filter', 'target_move'])[0])
        return self.env.ref('flexipharmacy.action_report_financial').report_action(self, data=data,
                                                                                   config=False)

    def print_xls(self):
        report_obj = self.env['report.flexipharmacy.report_financial']
        data = {'form': self.read(
            ['account_report_id', 'date_from_cmp', 'date_to_cmp', 'journal_ids', 'filter_cmp', 'target_move'])[0]}
        for field in ['account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(data)
        # res['data']['form']['comparison_context'] = comparison_context
        if comparison_context.get('date_from'):
            comparison_context['date_from'] = str(self.date_from_cmp)
        if comparison_context.get('date_to'):
            comparison_context['date_to'] = str(self.date_to_cmp)

        datas = {'account_report_id': [self.account_report_id.id, 'Profit and Loss'],
                 'company_id': [self.company_id.id, self.company_id.name], 'comparison_context': comparison_context,
                 'date_from': str(self.date_from) if self.date_from else False,
                 'date_from_cmp': str(self.date_from_cmp) if self.date_from_cmp else False,
                 'date_to': str(self.date_to) if self.date_to else False,
                 'date_to_cmp': str(self.date_to_cmp) if self.date_to_cmp else False,
                 'debit_credit': str(self.debit_credit) if self.debit_credit else False,
                 'enable_filter': self.enable_filter, 'filter_cmp': self.filter_cmp, 'id': self.id,
                 'journal_ids': False, 'label_filter': self.label_filter, 'target_move': self.target_move,
                 'used_context': {
                     'company_id': self.env.user.company_id.id,
                     'date_from': str(self.date_from) if self.date_from else False,
                     'date_to': str(self.date_to) if self.date_to else False,
                     'journal_ids': False,
                     'lang': self.env.user.lang,
                     'state': self.target_move,
                     'strict_range': comparison_context.get('strict_range') if comparison_context.get(
                         'strict_range') else False,
                 }}
        lines = report_obj.get_account_lines(datas)
        styleP = xlwt.XFStyle()
        stylePC = xlwt.XFStyle()
        styleBorder = xlwt.XFStyle()
        fontbold = xlwt.XFStyle()
        normal_style = xlwt.XFStyle()
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        alignment_lft = xlwt.Alignment()
        alignment_lft.horz = xlwt.Alignment.HORZ_LEFT
        alignment_rgt = xlwt.Alignment()
        alignment_rgt.horz = xlwt.Alignment.HORZ_RIGHT
        font = xlwt.Font()
        fontP = xlwt.Font()
        fontN = xlwt.Font()
        borders = xlwt.Borders()
        borders.bottom = xlwt.Borders.THIN
        borders.top = xlwt.Borders.THIN
        borders.right = xlwt.Borders.THIN
        borders.left = xlwt.Borders.THIN
        font.bold = False
        fontP.bold = True
        styleP.font = font
        # stylePC.font = fontP
        stylePC.alignment = alignment_lft
        fontbold.alignment = alignment_rgt
        styleBorder.font = fontP
        stylePC.font = fontP
        # fontbold.font = fontP
        styleBorder.alignment = alignment
        styleBorder.borders = borders
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Aged Payable")
        worksheet.col(0).width = 5600
        worksheet.col(1).width = 5600
        worksheet.col(2).width = 5600
        worksheet.col(3).width = 5600
        worksheet.write_merge(0, 2, 0, 3,
                              self.company_id.name + '\n' + self.company_id.email + '\n' + self.company_id.phone,
                              style=styleBorder)
        worksheet.write_merge(3, 3, 0, 3,
                              'Balance Sheet' if self._context.get('from_balance_sheet') else 'Profit and Loss',
                              style=styleBorder)
        worksheet.write_merge(4, 4, 0, 3,
                              'Target Moves : ' + 'All Entries' if self.target_move == 'all' else 'Target Moves : All Posted Entries')

        if self.date_from and self.date_to:
            worksheet.write_merge(5, 5, 0, 3,
                                  'Date From : ' + str(self.date_from) + ' ' + 'Date To : ' + str(self.date_to))
        row = 8
        if self.debit_credit:
            fontbold.font = fontP
            worksheet.write_merge(7, 7, 0, 0, 'Name', stylePC)
            worksheet.write_merge(7, 7, 1, 1, 'Debit', stylePC)
            worksheet.write_merge(7, 7, 2, 2, 'Credit', stylePC)
            worksheet.write_merge(7, 7, 3, 3, 'Balance', fontbold)
            for each in lines:
                fontbold.font = fontN
                normal_style.font = fontN
                if not each.get('level') > 3:
                    fontbold.font = fontP
                    normal_style.font = fontP
                if each.get('level') != 0:
                    worksheet.write_merge(row, row, 0, 0, each.get('name'), normal_style)
                    worksheet.write_merge(row, row, 1, 1, formatLang(self.env, float(each.get('debit')),
                                                                     currency_obj=self.env.user.company_id.currency_id),
                                          fontbold)
                    worksheet.write_merge(row, row, 2, 2, formatLang(self.env, float(each.get('credit')),
                                                                     currency_obj=self.env.user.company_id.currency_id),
                                          fontbold)
                    worksheet.write_merge(row, row, 3, 3, formatLang(self.env, float(each.get('balance')),
                                                                     currency_obj=self.env.user.company_id.currency_id),
                                          fontbold)
                    row += 1
        if not self.enable_filter and not self.debit_credit:
            fontbold.font = fontP
            worksheet.write_merge(7, 7, 0, 0, 'Name', stylePC)
            worksheet.write_merge(7, 7, 1, 1, 'Balance', fontbold)
            for each in lines:
                fontbold.font = fontN
                normal_style.font = fontN
                if not each.get('level') > 3:
                    fontbold.font = fontP
                    normal_style.font = fontP
                if each.get('level') != 0:
                    worksheet.write_merge(row, row, 0, 0, each.get('name'), normal_style)
                    worksheet.write_merge(row, row, 1, 1, formatLang(self.env, float(each.get('balance')),
                                                                     currency_obj=self.env.user.company_id.currency_id),
                                          fontbold)
                    row += 1
        if self.enable_filter and not self.debit_credit:
            fontbold.font = fontP
            worksheet.write_merge(7, 7, 0, 0, 'Name', stylePC)
            worksheet.write_merge(7, 7, 1, 1, 'Debit', fontbold)
            worksheet.write_merge(7, 7, 2, 2, str(self.label_filter) if self.label_filter else '', fontbold)
            for each in lines:
                if each.get('level') != 0:
                    fontbold.font = fontN
                    normal_style.font = fontN
                    if not each.get('level') > 3:
                        fontbold.font = fontP
                        normal_style.font = fontP
                    worksheet.write_merge(row, row, 0, 0, each.get('name'), normal_style)
                    worksheet.write_merge(row, row, 1, 1, formatLang(self.env, float(each.get('balance')),
                                                                     currency_obj=self.env.user.company_id.currency_id),
                                          fontbold)
                    worksheet.write_merge(row, row, 2, 2, formatLang(self.env, float(each.get('balance_cmp')),
                                                                     currency_obj=self.env.user.company_id.currency_id),
                                          fontbold)
                    row += 1
        file_data = io.BytesIO()
        workbook.save(file_data)
        self.write({
            'state': 'get',
            'data': base64.encodestring(file_data.getvalue()),
            'name': 'balance_sheet.xls' if self._context.get('from_balance_sheet') else 'profit_loss.xls'
        })
        return {
            'name': 'Profit & Loss',
            'type': 'ir.actions.act_window',
            'res_model': 'accounting.report.profit.loss',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new'
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
