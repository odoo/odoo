# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

BILLABLE_TYPES = [
    ('01_revenues_fixed', 'Revenues Fixed Price'),
    ('05_revenues_milestones', 'Revenues Milestones'),
    ('07_revenues_manual', 'Revenues Manual'),
    ('10_service_revenues', 'Service Revenues'),
    ('11_other_revenues', 'Other Revenues'),
    ('12_other_costs', 'Other Costs'),
]


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    billable_type = fields.Selection(BILLABLE_TYPES, string="Billable Type",
        compute='_compute_project_billable_type', compute_sudo=True, store=True, readonly=True)

    @api.depends('so_line.product_id', 'amount')
    def _compute_project_billable_type(self):
        for line in self:
            if line.amount >= 0 and line.unit_amount >= 0:
                if line.so_line and line.so_line.product_id.type == 'service':
                    line.billable_type = '10_service_revenues'
                else:
                    if line.product_id.invoice_policy == 'delivery':
                        service_type = line.product_id.service_type
                        if service_type == 'milestones':
                            invoice_type = '05_revenues_milestones'
                        elif service_type == 'manual':
                            invoice_type = '07_revenues_manual'
                        else:
                            invoice_type = '01_revenues_fixed'
                    elif line.product_id.invoice_policy == 'order':
                        invoice_type = '01_revenues_fixed'
                    else:
                        invoice_type = '11_other_revenues'
                    line.billable_type = invoice_type
            else:
                line.billable_type = '12_other_costs'
