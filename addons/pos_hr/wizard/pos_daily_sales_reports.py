# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosDailySalesReportsWizard(models.TransientModel):
    _inherit = 'pos.daily.sales.reports.wizard'

    add_report_per_employee = fields.Boolean(string='Add a report per each employee', default=True)
    employee_ids = fields.Many2many('hr.employee', compute='_compute_employee_ids')

    def _get_report_data(self):
        return {
            **super()._get_report_data(),
            'employee_ids': self.employee_ids.ids if self.add_report_per_employee else [],
        }

    @api.depends('pos_session_id')
    def _compute_employee_ids(self):
        for wizard in self:
            wizard.employee_ids = wizard.pos_session_id._get_order_employees() if wizard.pos_session_id else False

    @api.onchange('pos_session_id')
    def _onchange_pos_session_id(self):
        self.ensure_one()
        if self.pos_session_id and not self.employee_ids:
            self.add_report_per_employee = False
