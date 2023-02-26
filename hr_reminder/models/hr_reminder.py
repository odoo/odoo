# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields


class HrPopupReminder(models.Model):
    _name = 'hr.reminder'

    name = fields.Char(string='Title', required=True)
    model_name = fields.Many2one('ir.model', help="Choose the model name", string="Model", required=True, ondelete='cascade', domain="[('model', 'like','hr')]")
    model_field = fields.Many2one('ir.model.fields', string='Field', help="Choose the field",
                                  domain="[('model_id', '=',model_name),('ttype', 'in', ['datetime','date'])]",
                                  required=True, ondelete='cascade')
    search_by = fields.Selection([('today', 'Today'),
                                  ('set_period', 'Set Period'),
                                  ('set_date', 'Set Date'), ],
                                 required=True, string="Search By")
    days_before = fields.Integer(string='Reminder before', help="NUmber of days before the reminder")
    active = fields.Boolean(string="Active", default=True)
    # exclude_year = fields.Boolean(string="Consider day alone")
    reminder_active = fields.Boolean(string="Reminder Active", help="Reminder active")
    date_set = fields.Date(string='Select Date', help="Select the reminder set date")
    date_from = fields.Date(string="Start Date", help="Start date")
    date_to = fields.Date(string="End Date", help="End date")
    expiry_date = fields.Date(string="Reminder Expiry Date", help="Expiry date")
    company_id = fields.Many2one('res.company', string='Company', required=True, help="Company",
                                 default=lambda self: self.env.user.company_id)

    def reminder_scheduler(self):
        print("hlooo")
        now = fields.Datetime.from_string(fields.Datetime.now())
        print("8888",now)
        today = fields.Date.today()
        print("2222")
        obj = self.env['hr.reminder'].search([])
        for i in obj:
            if i.search_by != "today":
                if i.expiry_date and datetime.strptime(str(today), "%Y-%m-%d") == datetime.strptime(str(i.expiry_date), "%Y-%m-%d"):
                    i.active = False
                else:
                        if i.search_by == "set_date":
                            d1 = datetime.strptime(str(i.date_set), "%Y-%m-%d")
                            d2 = datetime.strptime(str(today), "%Y-%m-%d")
                            daydiff = abs((d2 - d1).days)
                            if daydiff <= i.days_before:
                                i.reminder_active = True
                            else:
                                i.reminder_active = False
                        elif i.search_by == "set_period":
                            d1 = datetime.strptime(str(i.date_from), "%Y-%m-%d")
                            d2 = datetime.strptime(str(today), "%Y-%m-%d")
                            daydiff = abs((d2 - d1).days)
                            if daydiff <= i.days_before:
                                i.reminder_active = True
                            else:
                                i.reminder_active = False
            else:
                i.reminder_active = True
