# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.onchange('project_id')
    def _onchange_project(self):
        if self.project_id.worksheet_template_id:
            self.worksheet_template_id = self.project_id.worksheet_template_id
