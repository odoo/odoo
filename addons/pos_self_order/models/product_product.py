# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from typing import List, Dict, Optional

from odoo import api, models, fields

from odoo.addons.point_of_sale.models.pos_config import PosConfig


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    self_order_available = fields.Boolean(
        string="Available in Self Order",
        help="If this product is available in the Self Order screens",
        default=True,
    )

    @api.constrains('available_in_pos')
    def _check_combo_inclusions(self):
        super()._check_combo_inclusions()
        self.self_order_available = False

    def write(self, vals_list):
        res = super().write(vals_list)
        if 'self_order_available' in vals_list:
            for record in self:
                for product in record.product_variant_ids:
                    product._send_availability_status()
        return res

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

        attributes = self._filter_applicable_attributes(
            self.env["pos.session"]._get_attributes_by_ptal_id()
        )
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

        display_price = price_info["total_included"] if pos_config.iface_tax_included == "total" else price_info["total_excluded"]
        display_price = self.lst_price if self.combo_ids else display_price

        return {
            "display_price": display_price,
            "lst_price": self.lst_price
        }

    def _get_product_for_ui(self, pos_config):
        self.ensure_one()
        return {
                "price_info": self._get_price_info(pos_config),
                "has_image": bool(self.image_1920),
                "attributes": self._get_attributes(pos_config),
                "name": self._get_name(),
                "id": self.id,
                "description_sale": self.description_sale,
                "pos_categ_ids": self.pos_categ_ids.mapped("name") or ["Other"],
                "pos_combo_ids": self.combo_ids.mapped("id") or False,
                "is_pos_groupable": self.uom_id.is_pos_groupable,
                "write_date": self.write_date.timestamp(),
                "self_order_available": self.self_order_available,
            }

    def _get_self_order_data(self, pos_config: PosConfig) -> List[Dict]:
        return [
            product._get_product_for_ui(pos_config)
            for product in self
        ]

    def write(self, vals_list):
        res = super().write(vals_list)
        if 'self_order_available' in vals_list:
            for record in self:
                record._send_availability_status()
        return res

    def _send_availability_status(self):
        config_self = self.env['pos.config'].sudo().search([('self_ordering_mode', '!=', 'nothing')])
        for config in config_self:
            if config.current_session_id and config.access_token:
                self.env['bus.bus']._sendone(f'pos_config-{config.access_token}', 'PRODUCT_CHANGED', {
                    'product': self._get_product_for_ui(config)
                })
