# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from typing import Dict

from odoo import models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    def _export_for_ui(self, orderline):
        return {
            "uuid": orderline.uuid,
            "note": orderline.note,
            **super()._export_for_ui(orderline),
        }

    def _get_description(self):
        """
        The pos sends a "description" key to the backend, which is a string containing the selected value for
        each attribute of the product, separated by a comma. In the db we end up storing the
        "full_product_name", which is composed of the product name and the description.
        :line.full_product_name: ex: "Desk Organizer (M, Leather)"
        :return: ex: "M, Leather"
        """
        self.ensure_one()
        description = re.findall("\(([^)]+)\)", self.full_product_name)
        if description:
            # It might happen that the product has a name with parenthesis. ex: "Salad (Vegie)"
            # In that case the full_product_name will be "Salad (Vegie) (Small)", but are interested in returning the variant "Small"
            # That's why we return the last element of the list
            return description[-1]
        return ""

    @staticmethod
    def _get_unique_keys():
        return ["product_id", "description", "customer_note"]


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _export_for_self_order(self) -> Dict:
        """
        Given an order, it returns a dictionary with the keys that we need in the frontend
        """
        self.ensure_one()
        return {
            "pos_reference": self.pos_reference,
            "access_token": self.access_token,
            "state": self.state,
            "date": str(self.date_order),
            "amount_total": self.amount_total,
            "amount_tax": self.amount_tax,
            "items": [
                {
                    "product_id": line.product_id.id,
                    "qty": line.qty,
                    "customer_note": line.customer_note,
                    "price_extra": line.product_id._get_price_info(
                        self.config_id,
                        line.price_extra,
                    ),
                    "description": line._get_description(),
                }
                for line in self.lines
            ],
        }
