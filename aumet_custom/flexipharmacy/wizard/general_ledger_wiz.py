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
from odoo import api, fields, models, _
import xlwt
import io
import base64
from odoo.tools.misc import formatLang, format_date


class GeneralLedgerReportWizard(models.TransientModel):
    _name = "account.general.ledger.wiz"
    _description = "General Ledger Report"

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string='Start Date', required=False)
    date_to = fields.Date(string='End Date', required=False)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')
    display_account = fields.Selection([('all', 'All'), ('movement', 'With movements'),
                                        ('not_zero', 'With balance is not equal to 0'), ],
                                       string='Display Accounts', required=True, default='movement')
    include_init_balance = fields.Boolean(string="Include Initial Balance")
    sortby = fields.Selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], string='Sort by',
                              required=True, default='sort_date')
    journal_ids = fields.Many2many('account.journal', 'account_report_general_ledger_journal_rel', 'account_id',
                                   'journal_id', string='Journals', required=True
                                   , default=lambda self: self.env['account.journal'].search([]))
    data = fields.Binary(string="Data")
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], string="State", default='choose')
    name = fields.Char(string='File Name', readonly=True)

    def print_pdf(self, data=None):
        data = {'ids': self.env.context.get('active_ids', []),
                'model': self.env.context.get('active_model', 'ir.ui.menu'), 'form': self.read(
                ['date_from', 'date_to', 'journal_ids', 'display_account', 'target_move', 'include_init_balance',
                 'sortby'])[0]}
        datas = {
            'ids': self._ids,
            'docs': self._ids,
            'model': 'account.general.ledger.wiz',
            'form': data['form']
        }
        return self.env.ref('flexipharmacy.report_general_ledger').report_action(self, data=datas)

    def print_xls(self, data=None):
        styleP = xlwt.XFStyle()
        stylePC = xlwt.XFStyle()
        styleBorder = xlwt.XFStyle()
        fontbold = xlwt.XFStyle()
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        alignment_right = xlwt.Alignment()
        alignment_right.horz = xlwt.Alignment.HORZ_LEFT
        alignment_lft = xlwt.Alignment()
        alignment_lft.horz = xlwt.Alignment.HORZ_RIGHT
        #         alignment_right.horz = xlwt.Alignment.HORZ_LEFT
        font = xlwt.Font()
        fontP = xlwt.Font()
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
        styleBorder.font = fontP
        fontbold.font = fontP
        styleBorder.alignment = alignment
        fontbold.alignment = alignment_lft
        styleBorder.borders = borders
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("General ledger")
        worksheet.col(0).width = 6000
        worksheet.col(3).width = 5000
        worksheet.col(2).width = 5000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 6000
        worksheet.col(4).width = 6000
        display_acccount = False
        if self.display_account == 'all':
            display_acccount = 'All'
        elif self.display_account == 'movement':
            display_acccount = 'With Movements'
        else:
            display_acccount = 'With balance is not equal to 0'

        worksheet.write_merge(0, 2, 0, 8,
                              self.company_id.name + '\n' + self.company_id.email + '\n' + self.company_id.phone,
                              style=styleBorder)
        worksheet.write_merge(4, 4, 0, 3, 'Journals:', style=fontbold)
        worksheet.write_merge(4, 4, 4, 5, 'Display Account', style=fontbold)
        worksheet.write_merge(4, 4, 6, 8, 'Target Moves:', style=fontbold)
        worksheet.write_merge(5, 5, 0, 3, ','.join(map(str, [each.code for each in self.journal_ids])), style=fontbold)
        worksheet.write_merge(5, 5, 4, 5, display_acccount, style=fontbold)
        worksheet.write_merge(5, 5, 6, 8, 'All Posted Entries' if self.target_move == 'posted' else 'All Entries',
                              style=fontbold)

        worksheet.write_merge(6, 6, 0, 2,
                              'Sort by : ' + 'Date' if self.sortby == 'sort_date' else 'Sort by : ' + 'Journal & Partner')
        worksheet.write_merge(6, 6, 3, 5, 'Date From : ' + str(self.date_from) if self.date_from else '')
        worksheet.write_merge(6, 6, 6, 8, 'Date To : ' + str(self.date_to) if self.date_to else '')
        worksheet.write_merge(7, 7, 0, 8)
        worksheet.write_merge(8, 8, 0, 0, 'Date', fontbold)
        worksheet.write_merge(8, 8, 1, 1, 'JRNL', fontbold)
        worksheet.write_merge(8, 8, 2, 2, 'Partner', fontbold)
        worksheet.write_merge(8, 8, 3, 3, 'Ref', fontbold)
        worksheet.write_merge(8, 8, 4, 4, 'Move', fontbold)
        worksheet.write_merge(8, 8, 5, 5, 'Entry Label', fontbold)
        worksheet.write_merge(8, 8, 6, 6, 'Debit', fontbold)
        worksheet.write_merge(8, 8, 7, 7, 'Credit', fontbold)
        worksheet.write_merge(8, 8, 8, 8, 'Balance', fontbold)
        report_obj = self.env['report.flexipharmacy.general_ledger_template']

        data = {'ids': self.env.context.get('active_ids', []),
                'model': self.env.context.get('active_model', 'ir.ui.menu'), 'form': self.read(
                ['date_from', 'date_to', 'journal_ids', 'display_account', 'target_move', 'include_init_balance',
                 'sortby'])[0]}

        data['form']['date_from'] = str(self.date_from) if self.date_from else ''
        data['form']['date_to'] = str(self.date_to) if self.date_to else ''
        datas = {
            'ids': self._ids,
            'docs': self._ids,
            'model': 'account.general.ledger.wiz',
            'form': data['form']
        }
        report_data = report_obj.with_context(active_model='account.general.ledger.wiz')._get_report_values(self,
                                                                                                            data=datas)
        row = 9
        for each in report_data['Accounts']:
            worksheet.write_merge(row, row, 0, 5, each['code'] + ' ' + each['name'], fontbold)
            worksheet.write_merge(row, row, 6, 6, formatLang(self.env, float(each['debit']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  fontbold)
            worksheet.write_merge(row, row, 7, 7, formatLang(self.env, float(each['credit']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  fontbold)
            worksheet.write_merge(row, row, 8, 8, formatLang(self.env, float(each['balance']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  fontbold)
            if self.include_init_balance:
                row += 1
                worksheet.write_merge(row, row, 4, 5, 'Initial Balance')
                worksheet.write_merge(row, row, 6, 6, formatLang(self.env, float(each['init_bal'][0]),
                                                                 currency_obj=self.env.user.company_id.currency_id))
                worksheet.write_merge(row, row, 7, 7, formatLang(self.env, float(each['init_bal'][1]),
                                                                 currency_obj=self.env.user.company_id.currency_id))
                worksheet.write_merge(row, row, 8, 8, formatLang(self.env, float(each['init_bal'][2]),
                                                                 currency_obj=self.env.user.company_id.currency_id))
            row += 1
            for each_line in each['move_lines']:
                worksheet.write_merge(row, row, 0, 0, str(each_line['ldate']))
                worksheet.write_merge(row, row, 1, 1, each_line['lcode'])
                worksheet.write_merge(row, row, 2, 2, each_line['partner_name'])
                worksheet.write_merge(row, row, 3, 3, each_line['lref'])
                worksheet.write_merge(row, row, 4, 4, each_line['move_name'])
                worksheet.write_merge(row, row, 5, 5, each_line['lname'])
                worksheet.write_merge(row, row, 6, 6, formatLang(self.env, float(each_line['debit']),
                                                                 currency_obj=self.env.user.company_id.currency_id),
                                      stylePC)
                worksheet.write_merge(row, row, 7, 7, formatLang(self.env, float(each_line['credit']),
                                                                 currency_obj=self.env.user.company_id.currency_id),
                                      stylePC)
                worksheet.write_merge(row, row, 8, 8, formatLang(self.env, float(each_line['balance']),
                                                                 currency_obj=self.env.user.company_id.currency_id),
                                      stylePC)
                row += 1
        file_data = io.BytesIO()
        workbook.save(file_data)
        self.write({
            'state': 'get',
            'data': base64.encodestring(file_data.getvalue()),
            'name': 'general_ledger.xls'
        })
        return {
            'name': 'General ledger',
            'type': 'ir.actions.act_window',
            'res_model': 'account.general.ledger.wiz',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new'
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
