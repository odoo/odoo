# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.onchange('service_tracking')
    def _onchange_service_tracking(self):
        if self.service_tracking == 'no':
            self.project_id = False
            self.project_template_id = False
        elif self.service_tracking == 'task_global_project':
            self.project_template_id = False
        elif self.service_tracking in ['task_in_project', 'project_only']:
            self.project_id = False

    def _inverse_service_policy(self):
        for product in self:
            if product.service_policy:

                product.invoice_policy, product.service_type = self.product_tmpl_id._get_service_to_general(product.service_policy)

    def write(self, vals):
        if 'type' in vals and vals['type'] != 'service':
            vals.update({
                'service_tracking': 'no',
                'project_id': False
            })
        return super().write(vals)
