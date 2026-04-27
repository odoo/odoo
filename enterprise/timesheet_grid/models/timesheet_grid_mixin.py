# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.tools import float_round


class TimesheetGridMixin(models.AbstractModel):
    _name = 'timesheet.grid.mixin'
    _description = 'Timesheet Grid mixin'

    @api.model
    def get_planned_and_worked_hours(self, ids):
        """
        Method called by the timesheet widgets on the frontend in gridview to get information
        about the hours allocated and worked for each record.
        """
        company = self.env.company
        uom = company.timesheet_encode_uom_id
        day_uom = self.env.ref('uom.product_uom_day')
        rounding = len(str(format(company.timesheet_encode_uom_id.rounding, 'f')).split('.')[1].split('1')[0]) + 1
        hours_per_day = company.resource_calendar_id.hours_per_day
        def convert_hours_to_company_uom(hours):
            return float_round(hours / hours_per_day, precision_digits=rounding) if uom == day_uom else hours

        records = self.search_read(
            self.get_planned_and_worked_hours_domain(ids),
            ['id', self.get_allocated_hours_field()] + self.get_worked_hours_fields(),
        )

        records_per_id = dict.fromkeys(ids, {})
        uom_name = uom.name.lower()
        for record in records:
            records_per_id[record['id']] = {
                'allocated_hours': convert_hours_to_company_uom(record[self.get_allocated_hours_field()]),
                'uom': uom_name,
                'worked_hours': convert_hours_to_company_uom(sum([record[field] for field in self.get_worked_hours_fields()])),
            }
        return records_per_id

    def get_planned_and_worked_hours_domain(self, ids):
        return [('id', 'in', ids)]
