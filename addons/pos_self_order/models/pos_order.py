# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from typing import Dict, Union

from odoo import models, fields


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    # For the moment we need this to keep attributes consistency between the server and client_side.
    selected_attributes = fields.Json(string="Selected Attributes")

    # FIXME: uuid already pass in pos and move note in pos_restaurant.
    def _export_for_ui(self, orderline):
        return {
            'uuid': orderline.uuid,
            'note': orderline.note,
            **super()._export_for_ui(orderline),
        }


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _export_for_self_order(self) -> Dict:
        self.ensure_one()

        return {
            "id": self.id,
            "pos_config_id": self.config_id.id,
            "pos_reference": self.pos_reference,
            "access_token": self.access_token,
            "state": self.state,
            "date": str(self.date_order),
            "amount_total": self.amount_total,
            "amount_tax": self.amount_tax,
            "lines": [
                {
                    "id": line.id,
                    "price_subtotal": line.price_subtotal,
                    "price_subtotal_incl": line.price_subtotal_incl,
                    "product_id": line.product_id.id,
                    "selected_attributes": line.selected_attributes,
                    "uuid": line.uuid,
                    "qty": line.qty,
                    "customer_note": line.customer_note,
                    "full_product_name": line.full_product_name,
                }
                for line in self.lines
            ],
        }
