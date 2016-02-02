# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)

from odoo import fields, models


class ResCompany(models.Model):
    """Override company to add Header object link a company can have many header and logos"""

    _inherit = "res.company"

    header_image = fields.Many2many('ir.header_img', 'company_img_rel', 'company_id', 'img_id', 'Available Images')
    header_webkit = fields.Many2many('ir.header_webkit', 'company_html_rel', 'company_id', 'html_id', 'Available html')
