# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarPopoverDeleteWizardHomework(models.TransientModel):
    _name = 'calendar.popover.delete.wizard.homework'
    _description = 'Calendar Popover Delete Wizard Homework'

    hr_employee_location_id = fields.Many2one('hr.employee.location', required=True)
    start_date = fields.Date(required=True)
    delete = fields.Selection([
        ('one', "Delete only this day's work location"),
        ('all', "Delete this work location for everyweek")],
        default='one', required=True)

    def remove_default_work_location(self):
        self.ensure_one()
        if self.delete == 'one':
            self.hr_employee_location_id.add_removed_work_location(self.start_date)
        else:
            self.hr_employee_location_id.delete_default_worklocation()
