# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

BILLABLE_TYPES = [
    ('01_revenues_fixed', 'Service Revenue (Fixed Price)'),
    ('03_service_revenues', 'Service Revenue (Time & Materials)'),
    ('05_revenues_milestones', 'Service Revenue (Milestones)'),
    ('07_revenues_manual', 'Service Revenue (Manual)'),
    ('11_materials', 'Materials'),
    ('14_other_revenues', 'Other Revenue'),
    ('20_vendor_bill', 'Vendor Bills'),
    ('30_other_costs', 'Other Costs'),
]

REVENUE_BILLABLE_TYPES = [
    '01_revenues_fixed',
    '03_service_revenues',
    '05_revenues_milestones',
    '07_revenues_manual',
    '11_materials',
    '14_other_revenues',
]


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    billable_type = fields.Selection(BILLABLE_TYPES, string="Billable Type",
        compute='_compute_project_billable_type', compute_sudo=True, store=True, readonly=True)

    category_report = fields.Selection(
        [('costs', 'Costs'), ('revenues', 'Revenue')],
        compute='_compute_category_report', compute_sudo=True, store=True, readonly=True)

    @api.depends('so_line.product_id', 'product_id', 'amount', 'category')
    def _compute_project_billable_type(self):
        for line in self:
            if line.amount >= 0 and line.unit_amount >= 0:
                if line.so_line and line.so_line.product_id.type == 'service':
                    invoice_type = '03_service_revenues'
                elif line.product_id.type == 'consu':
                    invoice_type = '11_materials'
                elif line.product_id.invoice_policy == 'delivery':
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
                    invoice_type = '14_other_revenues'
                line.billable_type = line._get_invoice_type(invoice_type)
            else:
                line._set_billable_cost()

    def _set_billable_cost(self):
        if self.category == 'vendor_bill':
            self.billable_type = '20_vendor_bill'
        else:
            self.billable_type = '30_other_costs'

    def _get_invoice_type(self, invoice_type):
        return invoice_type

    @api.depends('billable_type')
    def _compute_category_report(self):
        for line in self:
            if line.billable_type in REVENUE_BILLABLE_TYPES:
                line.category_report = 'revenues'
            else:
                line.category_report = 'costs'

    def action_open_account_analytic_line_origine(self):
        self.ensure_one()
        if (self.so_line):
            return {
                'res_model': self.so_line._name,
                'type': 'ir.actions.act_window',
                'views': [[False, "form"]],
                'res_id': self.so_line.id,
            }
        return {
            'res_model': self._name,
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'res_id': self.id,
        }
