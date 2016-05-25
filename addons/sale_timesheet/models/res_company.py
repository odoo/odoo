# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _get_default_uom_id(self):
        return self.env.ref("product.product_uom_hour", raise_if_not_found=False)

    project_time_mode_id = fields.Many2one('product.uom', 'Timesheet UoM', default=_get_default_uom_id)
