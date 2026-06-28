# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.website_sale import const


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    def _get_extra_price(self, currency):
        self.ensure_one()
        if not self.show_price_extra:
            return 0.0

        if not self.price_extra:
            return 0.0

        price_extra = self.price_extra
        if not price_extra:
            return price_extra

        product_template = self.product_tmpl_id
        if currency != product_template.currency_id:
            price_extra = self.currency_id._convert(from_amount=price_extra, to_currency=currency)

        return self.product_tmpl_id._apply_taxes_to_price(price_extra, currency)

    def _split_standard_from_custom_attributes(self):
        """Split PTAVs into directly mapped fields and the rest.

        Direct fields are attributes whose external_identifier matches a known
        identifier used across Microdata, GMC Feeds, and Tracking.

        :return: A tuple of:
            - dict of {external_identifier: value} for known direct fields
            - dict of {attribute_name: value} for all other attributes
        :rtype: tuple(dict, dict)
        """
        direct = {}
        others = {}
        for ptav in self:
            external_id = ptav.attribute_id.external_identifier
            ext_id = external_id and external_id.lower()
            value = ptav.product_attribute_value_id.name
            if ext_id and ext_id in const.DIRECT_MAPPED_ATTRIBUTE_IDENTIFIERS:
                direct[ext_id] = value
            elif external_id:
                others[external_id] = value
        return direct, others
