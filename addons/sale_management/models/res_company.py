# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _check_company_auto = True

    sale_order_template_id = fields.Many2one(
        "sale.order.template", string="Default Sale Template",
        domain="['|', ('company_id', '=', False), ('company_id', '=', id)]",
        check_company=True,
    )
