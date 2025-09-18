# Part of Odoo. See LICENSE file for full copyright and licensing details.

# flake8: noqa: F401

# don't try to be a good boy and sort imports alphabetically.
# `product.template` should be initialised before `product.product`
from . import (
    product_template,
    product_product,
    ir_attachment,
    product_attribute,
    product_attribute_custom_value,
    product_attribute_value,
    product_catalog_mixin,
    product_category,
    product_combo,
    product_combo_item,
    product_document,
    product_pricelist,
    product_pricelist_item,
    product_supplierinfo,
    product_tag,
    product_template_attribute_line,
    product_template_attribute_exclusion,
    product_template_attribute_value,
    product_uom,
    res_company,
    res_config_settings,
    res_country_group,
    res_currency,
    res_partner,
    uom_uom,
)
