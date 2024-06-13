# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models
from odoo.tools import populate, groupby

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    _populate_dependencies = ["res.partner", "stock.picking.type"]

    def _populate_factories(self):
        res = super()._populate_factories()
        picking_types = self.env['stock.picking.type'].search([('code', '=', 'incoming')])

        picking_types_by_company = dict(groupby(picking_types, key=lambda par: par.company_id.id))
        picking_types_inter_company = self.env['stock.picking.type'].concat(*picking_types_by_company.get(False, []))
        picking_types_by_company = {com: self.env['stock.picking.type'].concat(*pt) | picking_types_inter_company for com, pt in picking_types_by_company.items() if com}

        def get_picking_type_id(values=None, random=None, **kwargs):
            return random.choice(picking_types_by_company[values["company_id"]]).id

        return res + [
            ("picking_type_id", populate.compute(get_picking_type_id))
        ]
