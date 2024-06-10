# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons import base as base
from .sale_order_template import SaleOrderTemplate


class ResCompany(base.models.Company):
    _check_company_auto = True

    sale_order_template_id = fields.Many2one[SaleOrderTemplate](
        string="Default Sale Template",
        domain="['|', ('company_id', '=', False), ('company_id', '=', id)]",
        check_company=True,
    )
