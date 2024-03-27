# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

from typing import List, Dict, Optional

from copy import deepcopy

from odoo import models

from odoo.addons.point_of_sale.models.pos_config import PosConfig


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_name(self) -> str:
        """
        Returns the name of the product without the code.
        ex: product_sudo.display_name is '[FURN_7888] Desk Stand with Screen (Red)'
        :return: 'Desk Stand with Screen (Red)' (we remove the [FURN_7888] part)
        """
        self.ensure_one()
        return self.with_context(display_default_code=False).display_name

    def _filter_applicable_attributes(self, attributes_by_ptal_id: Dict) -> List[Dict]:
        """
        The attributes_by_ptal_id is a dictionary that contains all the attributes that have
        [('create_variant', '=', 'no_variant')]
        This method filters out the attributes that are not applicable to the product in self
        """
        self.ensure_one()
        return [
            attributes_by_ptal_id[id]
            for id in self.attribute_line_ids.ids
            if attributes_by_ptal_id.get(id) is not None
        ]

    def _get_attributes(self, pos_config_sudo: PosConfig) -> List[Dict]:
        self.ensure_one()

        attributes = self.env.context.get("cached_attributes_by_ptal_id")

        if attributes is None:
            attributes = self.env["pos.session"]._get_attributes_by_ptal_id()
            attributes = self._filter_applicable_attributes(attributes)
        else:
            # Performance trick to avoid unnecessary calls to _get_attributes_by_ptal_id()
            # Needs to be deep-copied because attributes is potentially mutated
            attributes = deepcopy(self._filter_applicable_attributes(attributes))

        return self._add_price_info_to_attributes(
            attributes,
            pos_config_sudo,
        )

    def _add_price_info_to_attributes(
        self, attributes: List[Dict], pos_config_sudo: PosConfig
    ) -> List[Dict]:
        """
        Here we replace the price_extra of each attribute value with a price_extra
        dictionary that includes the price with taxes included and the price with taxes excluded
        """
        self.ensure_one()
        for attribute in attributes:
            for value in attribute["values"]:
                value.update(
                    {
                        "price_extra": self._get_price_info(
                            pos_config_sudo, value.get("price_extra")
                        )
                    }
                )
        return attributes

    # FIXME: this method should be verified about price computation (pricelist taxes....)
    def _get_price_info(
        self, pos_config: PosConfig, price: Optional[float] = None, qty: int = 1
    ) -> Dict[str, float]:
        """
        Function that returns a dict with the price info of a given product
        """
        self.ensure_one()
        # if price == None it means that a price was not passed as a parameter, so we use the product's list price
        # it could happen that a price was passed, but it was 0; in that case we want to use this 0 as the argument,
        # and not the product's list price
        if price is None:
            price = pos_config.pricelist_id._get_product_price(
                self, qty, currency=pos_config.currency_id
            )
        price_info = pos_config.default_fiscal_position_id.map_tax(self.taxes_id).compute_all(
            price, pos_config.currency_id, qty, product=self
        )

        return {
            "list_price": price_info["total_included"]
            if pos_config.iface_tax_included == "total"
            else price_info["total_excluded"],
            "price_without_tax": price_info["total_excluded"],
            "price_with_tax": price_info["total_included"],
        }

    def _get_self_order_data(self, pos_config: PosConfig) -> List[Dict]:
        """
        returns the list of products with the necessary info for the self order app
        """
        attributes_by_ptal_id = self.env["pos.session"]._get_attributes_by_ptal_id()
        self = self.with_context(cached_attributes_by_ptal_id=attributes_by_ptal_id)
        return [
            {
                "price_info": product._get_price_info(pos_config),
                "has_image": bool(product.product_tmpl_id.image_128 or product.image_variant_128),
                "attributes": product._get_attributes(pos_config),
                "name": product._get_name(),
                "id": product.id,
                "description_sale": product.description_sale,
                "pos_categ_ids": product.pos_categ_ids.mapped("name") or ["Other"],
                "is_pos_groupable": product.uom_id.is_pos_groupable,
            }
            for product in self
        ]
