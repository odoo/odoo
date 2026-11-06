# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ------------------------------------------------------------------
    # Mileage category flag
    # ------------------------------------------------------------------
    # Marks an expense category (product with ``can_be_expensed``) whose
    # expenses are reimbursed per kilometre. The quick-submit wizard reads
    # this flag to switch to the mileage input (distance x company rate)
    # instead of a plain amount.
    od19_is_mileage_category = fields.Boolean(
        string='Mileage Category / หมวดค่าเดินทางตามระยะทาง',
        help='Tick when expenses of this category are reimbursed per '
             'kilometre.',
    )
