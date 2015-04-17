# -*- coding: utf-8 -*-
from openerp import models, fields, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_delivery_charge_product = fields.Boolean(_("Can be used in delivery charge"))
