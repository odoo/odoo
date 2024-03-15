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
    description_self_order = fields.Html(
        string="Product Description for Self Order",
    )

    @api.onchange('available_in_pos')
    def _on_change_available_in_pos(self):
        for record in self:
            if not record.available_in_pos:
                record.self_order_available = False

    def write(self, vals_list):
        if 'available_in_pos' in vals_list:
            if not vals_list['available_in_pos']:
                vals_list['self_order_available'] = False

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

    def _get_price_unit_after_fp(self, lst_price, currency, fiscal_position):
        self.ensure_one()

        taxes = self.taxes_id

        mapped_included_taxes = self.env['account.tax']
        new_included_taxes = self.env['account.tax']

        for tax in taxes:
            mapped_taxes = fiscal_position.map_tax(tax)
            if mapped_taxes and any(mapped_taxes.mapped('price_include')):
                new_included_taxes |= mapped_taxes
            if tax.price_include and not (tax in mapped_taxes):
                mapped_included_taxes |= tax

        if mapped_included_taxes:
            if new_included_taxes:
                price_untaxed = mapped_included_taxes.compute_all(
                    lst_price,
                    currency,
                    1,
                    handle_price_include=True,
                )['total_excluded']
                return new_included_taxes.compute_all(
                    price_untaxed,
                    currency,
                    1,
                    handle_price_include=False,
                )['total_included']
            else:
                return mapped_included_taxes.compute_all(
                    lst_price,
                    currency,
                    1,
                    handle_price_include=True,
                )['total_excluded']
        else:
            return lst_price

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

        # Declare variables, will be the return values.
        display_price_default = price
        display_price_alternative = price

        taxes_default = pos_config.default_fiscal_position_id.map_tax(self.taxes_id)
        taxes_alternative = pos_config.self_ordering_alternative_fp_id.map_tax(self.taxes_id)

        price_unit_default = self._get_price_unit_after_fp(
            price, pos_config.currency_id, pos_config.default_fiscal_position_id
        )
        price_unit_alternative = self._get_price_unit_after_fp(
            price, pos_config.currency_id, pos_config.self_ordering_alternative_fp_id
        )

        all_prices_default = taxes_default.compute_all(
            price_unit_default, pos_config.currency_id, qty, product=self
        )
        all_prices_alternative = taxes_alternative.compute_all(
            price_unit_alternative, pos_config.currency_id, qty, product=self
        )

        if self.combo_ids:
            display_price_default = self.lst_price
            display_price_alternative = self.lst_price
        else:
            if pos_config.iface_tax_included == 'total':
                display_price_default = all_prices_default["total_included"]
                display_price_alternative = all_prices_alternative["total_included"]
            else:
                display_price_default = all_prices_default["total_excluded"]
                display_price_alternative = all_prices_alternative["total_excluded"]

        return {
            'display_price_default': display_price_default,
            'display_price_alternative': display_price_alternative,
        }

    def _get_product_for_ui(self, pos_config):
        self.ensure_one()
        return {
                "price_info": self._get_price_info(pos_config),
                "has_image": bool(self.product_tmpl_id.image_128 or self.image_variant_128),
                "attributes": self._get_attributes(pos_config),
                "name": self._get_name(),
                "id": self.id,
                "description_self_order": self.description_self_order,
                "pos_categ_ids": self.pos_categ_ids.read(["id", "name"]) or [{"id": 0, "name": "Uncategorised"}],
                "pos_combo_ids": self.combo_ids.mapped("id") or False,
                "is_pos_groupable": self.uom_id.is_pos_groupable,
                "write_date": self.write_date.timestamp(),
                "self_order_available": self.self_order_available,
                "barcode": self.barcode,
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
