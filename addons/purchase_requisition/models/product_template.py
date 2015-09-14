# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchase_requisition = fields.Selection(
        [('rfq', 'Create a draft purchase order'),
         ('tenders', 'Propose a call for tenders')],
        string='Procurement',
        help="Check this box to generate Call for Tenders instead of generating "
             "requests for quotation from procurement.", default='rfq')
