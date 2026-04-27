# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    ytd_reset_day = fields.Integer(
        default=1,
        string='YTD Reset Day of the month',
        help="""Day where the YTD will be reset every year. If zero or negative, then the first day of the month will be selected instead.
        If greater than the last day of a month, then the last day of the month will be selected instead.""")
    ytd_reset_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')],
        default='1', string='YTD Reset Month')

    @api.constrains('ytd_reset_day', 'ytd_reset_month')
    def _check_valid_reset_date(self):
        for company in self:
            # We try if the date exists in 2023, which is not a leap year.
            max_possible_day = calendar.monthrange(2023, int(company.ytd_reset_month))[1]
            if company.ytd_reset_day < 1 or company.ytd_reset_day > max_possible_day:
                raise ValidationError(self.env._("The YTD reset day must be a valid day of the month : since the current month is %(month)s, it should be between 1 and %(day)s.",
                    month=company._fields['ytd_reset_month'].selection[int(company.ytd_reset_month) - 1][1],
                    day=max_possible_day
                ))

    def _create_dashboard_notes(self):
        user_lang = self.env.user.lang or self.env.company.partner_id.lang or 'en_US'
        note = self.env['ir.qweb']._render('hr_payroll.hr_payroll_note_demo_content', {'date_today': fields.Date.today().strftime(self.env['res.lang']._get_data(code=user_lang).date_format)})
        self.env['hr.payroll.note'].sudo().create([{
            'company_id': company.id,
            'name': self.env._('Note'),
            'note': note,
        } for company in self])

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._create_dashboard_notes()
        return companies

    def get_last_ytd_reset_date(self, target_date):
        self.ensure_one()
        last_ytd_reset_date = date(target_date.year, int(self.ytd_reset_month), self.ytd_reset_day)
        if last_ytd_reset_date > target_date:
            last_ytd_reset_date += relativedelta(years=-1)
        return last_ytd_reset_date
