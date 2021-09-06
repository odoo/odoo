# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
##################################company_id###############################################

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from datetime import date
import xlwt
import io
import base64
from odoo.tools.misc import formatLang, format_date


class AccountAgedReceivableReportPdf(models.TransientModel):
    _name = "aged.receivable"
    _description = "Account Aged Receivable Report"

    start_date = fields.Date(string="Start Date", required=True, default=date.today())
    period_length = fields.Integer(string="Period Length (days)", required=True, default=30)
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries')], string="Target Moves",
                                   default="posted")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    data = fields.Binary(string="Data")
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], string="State", default='choose')
    name = fields.Char(string='File Name', readonly=True)

    def generate_aged_receivable(self):
        if self.period_length <= 0:
            raise Warning(_('You must set a period length greater than 0.'))

        data = {'ids': self.env.context.get('active_ids', []),
                'model': self.env.context.get('active_model', 'ir.ui.menu'), 'form': self.read()[0]}
        datas = {
            'ids': self._ids,
            'docs': self._ids,
            'model': 'aged.receivable',
            'form': data['form']
        }
        return self.env.ref('flexipharmacy.report_aged_receivable').report_action(self, data=datas)

    def generate_account_receivable_xls(self):
        report_obj = self.env['report.flexipharmacy.aged_receivable_template']
        styleP = xlwt.XFStyle()
        stylePC = xlwt.XFStyle()
        styleBorder = xlwt.XFStyle()
        fontbold = xlwt.XFStyle()
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        alignment_rgt = xlwt.Alignment()
        alignment_rgt.horz = xlwt.Alignment.HORZ_RIGHT
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
        stylePC.alignment = alignment_rgt
        fontbold.alignment = alignment_rgt
        styleBorder.font = fontP
        fontbold.font = fontP
        styleBorder.alignment = alignment
        styleBorder.borders = borders
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Aged Receivable")
        worksheet.col(0).width = 5600
        worksheet.col(3).width = 5000
        worksheet.write_merge(0, 2, 0, 7,
                              self.company_id.name + '\n' + self.company_id.email + '\n' + self.company_id.phone,
                              style=styleBorder)
        worksheet.write_merge(3, 3, 0, 7, 'Aged Receivable', style=styleBorder)
        worksheet.write_merge(4, 4, 0, 0, 'Start Date :', style=styleBorder)
        worksheet.write_merge(4, 4, 1, 2, str(self.start_date), style=styleBorder)
        worksheet.write_merge(4, 4, 3, 3, "Period Length (days)", style=styleBorder)
        worksheet.write_merge(4, 4, 4, 5, self.period_length, style=styleBorder)
        worksheet.write_merge(5, 5, 0, 0, "Partner's:", style=styleBorder)
        worksheet.write_merge(5, 5, 1, 2, 'Receivable Accounts', style=styleBorder)
        worksheet.write_merge(5, 5, 3, 3, "Target Moves:", style=styleBorder)
        worksheet.write_merge(5, 5, 4, 5, 'All Posted Entries' if self.target_move == 'posted' else 'All Enteries',
                              style=styleBorder)
        worksheet.write_merge(6, 6, 0, 7, style=styleBorder)
        period_lenght = report_obj.get_time_interval(str(self.start_date), self.period_length)
        worksheet.write_merge(7, 7, 0, 0, 'Partners', style=styleBorder)
        worksheet.write_merge(7, 7, 1, 1, 'Not due', style=styleBorder)
        worksheet.write_merge(7, 7, 2, 2, period_lenght['4']['name'], style=styleBorder)
        worksheet.write_merge(7, 7, 3, 3, period_lenght['3']['name'], style=styleBorder)
        worksheet.write_merge(7, 7, 4, 4, period_lenght['2']['name'], style=styleBorder)
        worksheet.write_merge(7, 7, 5, 5, period_lenght['1']['name'], style=styleBorder)
        worksheet.write_merge(7, 7, 6, 6, period_lenght['0']['name'], style=styleBorder)
        worksheet.write_merge(7, 7, 7, 7, 'Total', style=styleBorder)
        accont_moveline, total, dummy = report_obj._get_partner_move_lines_custom(['receivable'], str(self.start_date),
                                                                                  self.target_move, self.period_length)
        if total:
            worksheet.write_merge(8, 8, 0, 0, 'Account Total')
            worksheet.write_merge(8, 8, 1, 1, formatLang(self.env, float(total[6]),
                                                         currency_obj=self.env.user.company_id.currency_id),
                                  style=fontbold)
            worksheet.write_merge(8, 8, 2, 2, formatLang(self.env, float(total[4]),
                                                         currency_obj=self.env.user.company_id.currency_id),
                                  style=fontbold)
            worksheet.write_merge(8, 8, 3, 3, formatLang(self.env, float(total[3]),
                                                         currency_obj=self.env.user.company_id.currency_id),
                                  style=fontbold)
            worksheet.write_merge(8, 8, 4, 4, formatLang(self.env, float(total[2]),
                                                         currency_obj=self.env.user.company_id.currency_id),
                                  style=fontbold)
            worksheet.write_merge(8, 8, 5, 5, formatLang(self.env, float(total[1]),
                                                         currency_obj=self.env.user.company_id.currency_id),
                                  style=fontbold)
            worksheet.write_merge(8, 8, 6, 6, formatLang(self.env, float(total[0]),
                                                         currency_obj=self.env.user.company_id.currency_id),
                                  style=fontbold)
            worksheet.write_merge(8, 8, 7, 7, formatLang(self.env, float(total[5]),
                                                         currency_obj=self.env.user.company_id.currency_id),
                                  style=fontbold)
        row = 9
        for each in accont_moveline:
            worksheet.write_merge(row, row, 0, 0, each['name'])
            worksheet.write_merge(row, row, 1, 1, formatLang(self.env, float(each['direction']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  stylePC)
            worksheet.write_merge(row, row, 2, 2, formatLang(self.env, float(each['4']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  stylePC)
            worksheet.write_merge(row, row, 3, 3, formatLang(self.env, float(each['3']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  stylePC)
            worksheet.write_merge(row, row, 4, 4, formatLang(self.env, float(each['2']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  stylePC)
            worksheet.write_merge(row, row, 5, 5, formatLang(self.env, float(each['1']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  stylePC)
            worksheet.write_merge(row, row, 6, 6, formatLang(self.env, float(each['1']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  stylePC)
            worksheet.write_merge(row, row, 7, 7, formatLang(self.env, float(each['total']),
                                                             currency_obj=self.env.user.company_id.currency_id),
                                  stylePC)
            row += 1
        file_data = io.BytesIO()
        workbook.save(file_data)
        self.write({
            'state': 'get',
            'data': base64.encodestring(file_data.getvalue()),
            'name': 'aged_receivable.xls'
        })
        return {
            'name': 'Aged Receivable',
            'type': 'ir.actions.act_window',
            'res_model': 'aged.receivable',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new'
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
