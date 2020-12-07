# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.models.pos_session import load_fields

load_fields("pos.payment.method", ["pos_mercury_config_id"])
