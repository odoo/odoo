# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _get_uom_hours(self):
        try:
            return self.env.ref("product.product_uom_hour")
        except ValueError:
            return False
    project_time_mode_id = fields.Many2one('product.uom', string='Timesheet UoM', default=_get_uom_hours)
