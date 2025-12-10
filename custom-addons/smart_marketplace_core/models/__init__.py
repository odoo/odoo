# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# First import models that EXTEND existing Odoo models (to add seller_id fields)
from . import product_template
from . import sale_order
from . import res_partner

# Then import new models that reference those extended models via One2many
from . import marketplace_seller
