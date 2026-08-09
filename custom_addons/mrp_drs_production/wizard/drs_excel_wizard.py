from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DRSProductionExcelWizard(models.TransientModel):
    _name = 'drs.production.excel.wizard'
    _description = 'DRS Excel Export Wizard'

    filter_type = fields.Selection([
        ('today', "Today's Work (عمل اليوم)"),
        ('custom', 'Custom Date Range (فترة محددة)'),
    ], string="Filter Type", default='today', required=True)

    date_from = fields.Date(string="From Date", default=fields.Date.context_today)
    date_to = fields.Date(string="To Date", default=fields.Date.context_today)
    machine_number = fields.Selection([
        ('all', 'All Machines'),
        ('311', '311'),
        ('312', '312'),
    ], string="Machine", default='all')

    def action_print_excel(self):
        domain = []
        if self.filter_type == 'today':
            today = fields.Date.context_today(self)
            domain.append(('date', '=', today))
        else:
            if self.date_from:
                domain.append(('date', '>=', self.date_from))
            if self.date_to:
                domain.append(('date', '<=', self.date_to))

        if self.machine_number and self.machine_number != 'all':
            domain.append(('machine_number', '=', self.machine_number))

        records = self.env['mrp.drs.production'].search(domain)
        if not records:
            raise UserError(_("No production reports found for the selected criteria."))

        return self.env['mrp.drs.production']._generate_excel_action(records)
