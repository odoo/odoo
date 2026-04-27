# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression

DEFAULT_INVOICED_TIMESHEET = 'all'


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'timesheet.grid.mixin']

    @api.depends('analytic_line_ids.validated')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        values = super(SaleOrderLine, self)._timesheet_create_project_prepare_values()
        values['allow_timesheets'] = True
        return values

    def _timesheet_compute_delivered_quantity_domain(self):
        domain = super(SaleOrderLine, self)._timesheet_compute_delivered_quantity_domain()
        # force to use only the validated timesheet
        param_invoiced_timesheet = self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        if param_invoiced_timesheet == 'approved':
            domain = expression.AND([domain, [('validated', '=', True)]])
        return domain

    def get_allocated_hours_field(self):
        return 'product_uom_qty'

    def get_worked_hours_fields(self):
        return ['qty_delivered']

    def get_planned_and_worked_hours_domain(self, ids):
        return super().get_planned_and_worked_hours_domain(ids) + [('qty_delivered_method', 'not in', ['manual', 'milestones'])]
