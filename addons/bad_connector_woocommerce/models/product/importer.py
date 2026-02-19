import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError

from ...components import utils

# pylint: disable=W7950

_logger = logging.getLogger(__name__)


class WooProductProductBatchImporter(Component):
    """Batch Importer the WooCommerce Product"""

    _name = "woo.product.product.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.product.product"


class WooProductImageUrlImporter(Component):
    """
    Import translations for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products and products' Image importers.
    This importer is responsible for fetching image data from an external
    source based on the provided image URL.
    """

    _name = "woo.product.image.url.importer"
    _inherit = "woo.importer"
    _usage = "product.image.importer"

    def run(self, external_id, binding, image_data):
        """
        Import and associate product images.
        :param image_data: List of image information.
        """
        image_ids = []
        for index, image_info in enumerate(image_data):
            if index == 0:
                image_record = self._import_primary_image(binding, image_info)
            else:
                image_record = self._import_secondary_image(image_info)
            image_ids.append(image_record.id)
        if image_ids:
            binding.write({"woo_product_image_url_ids": [(6, 0, image_ids)]})

    def _find_existing_image(self, name, url):
        """
        Find an existing image record based on name and URL.
        :param name: The name of the image.
        :param url: The URL of the image.
        :return: Existing image record or None if not found.
        """
        return self.env["woo.product.image.url"].search(
            [("name", "=", name), ("url", "=", url)], limit=1
        )

    def _import_primary_image(self, binding, image_info):
        """
        Import primary product image.
        :param image_info: Information about the primary image.
        """
        name = image_info.get("name")
        image_url = image_info.get("src")
        alt = image_info.get("alt")
        image_record = self._find_existing_image(name, image_url)
        if not image_record:
            image_values = {
                "name": name,
                "url": image_url,
                "alt": alt,
            }
            image_record = self.env["woo.product.image.url"].create(image_values)
        binary_data = utils.fetch_image_data(image_url)
        if not binary_data:
            return image_record
        binding.write({"image_1920": binary_data})
        return image_record

    def _import_secondary_image(self, image_info):
        """
        Get or create a secondary image record.
        :param image_info: Information about the secondary image.
        :return: Secondary image record.
        """
        name = image_info.get("name")
        url = image_info.get("src")
        alt = image_info.get("alt")
        existing_image = self._find_existing_image(name, url)
        image_values = {
            "name": name,
            "url": url,
            "alt": alt,
        }
        if not existing_image:
            return self.env["woo.product.image.url"].create(image_values)
        return existing_image


class WooProductProductImportMapper(Component):
    """Impoter Mapper for the WooCommerce Product"""

    _name = "woo.product.product.import.mapper"
    _inherit = "woo.product.common.mapper"
    _apply_on = "woo.product.product"
    _map_child_fallback = "woo.map.child.import"
    children = [
        (
            "downloads",
            "woo_downloadable_product_ids",
            "woo.downloadable.product",
        ),
    ]

    @only_create
    @mapping
    def odoo_id(self, record):
        """Mapping for odoo id"""
        if record.get("type") != "variation":
            return {}

        # Find the co-responding template for variation
        binder = self.binder_for("woo.product.template")
        template_id = binder.to_internal(record.get("parent_id"), unwrap=True)

        # Extract attributes from the WooCommerce product variant data
        attributes = record.get("attributes", [])

        # Search for product.template.attribute.value records
        search_domain = [
            ("product_tmpl_id", "=", template_id.id),
            ("attribute_id.name", "in", [attr["name"] for attr in attributes]),
            ("name", "in", [attr["option"] for attr in attributes]),
        ]
        combination = self.env["product.template.attribute.value"].search(search_domain)

        # Get the variation record
        matching_variant = template_id._get_variant_for_combination(combination)
        return {"odoo_id": matching_variant.id} if matching_variant else {}

    @mapping
    def woo_product_name(self, record):
        """Mapping for woo_product_name"""
        name = record.get("name")
        if not name:
            raise MappingError(
                _("Product name doesn't exist for Product ID %s Please check")
                % record.get("id")
            )
        return {"woo_product_name": name}

    @mapping
    def product_tmpl_id(self, record):
        """Mapping for product_tmpl_id"""
        binder = self.binder_for("woo.product.template")
        template_id = binder.to_internal(record.get("parent_id"), unwrap=True)
        return {"product_tmpl_id": template_id.id} if template_id else {}

    @mapping
    def stock_management(self, record):
        """Mapping for Stock Management"""
        manage_stock = record.get("manage_stock")
        return {"stock_management": True} if manage_stock is True else {}

    @mapping
    def woo_product_qty(self, record):
        """Mapping for WooCommerce Product qty"""
        return (
            {"woo_product_qty": record.get("stock_quantity")}
            if record.get("stock_quantity")
            else {}
        )

    @mapping
    def price(self, record):
        """Mapping for Standard Price"""
        price = record.get("price")
        return {"price": price} if price else {}

    @mapping
    def regular_price(self, record):
        """Mapping for Regular Price"""
        regular_price = record.get("regular_price")
        return {"regular_price": regular_price} if regular_price else {}

    @mapping
    def status(self, record):
        """Mapping for status"""
        status = record.get("status")
        return {"status": status} if status else {}

    @mapping
    def tax_status(self, record):
        """Mapping for tax_status"""
        tax_status = record.get("tax_status")
        return {"tax_status": tax_status} if tax_status else {}

    @mapping
    def stock_status(self, record):
        """Mapping for stock_status"""
        stock_status = record.get("stock_status")
        return {"stock_status": stock_status} if stock_status else {}

    @mapping
    def downloadable_product(self, record):
        """Mapping of downloadable product"""
        downloadable_product = record.get("downloadable")
        return {"downloadable_product": True} if downloadable_product else {}

    def _unlink_downloadable_product(self, map_record, product_ids):
        """Unlink downloadable products if they are removed from woocommerce."""
        product_binder = self.binder_for("woo.product.product")
        product_id = map_record.source.get("id")
        downloadable_in_record = set()
        if product_id:
            product = product_binder.to_internal(product_id)
            if product:
                downloadable_in_record = set(
                    product.woo_downloadable_product_ids.mapped("external_id")
                )

        removable_product = downloadable_in_record - set(product_ids)
        if removable_product:
            records_to_unlink = self.env["woo.downloadable.product"].search(
                [("external_id", "in", list(removable_product))]
            )
            records_to_unlink.unlink()

    def finalize(self, map_record, values):
        """Unlink downloadable product that no longer exist"""
        values = super(WooProductProductImportMapper, self).finalize(map_record, values)
        product_ids = [
            value[2].get("external_id")
            for value in values.get("woo_downloadable_product_ids")
        ]
        if product_ids:
            self._unlink_downloadable_product(map_record, product_ids)
        return values


class WooProductProductImporter(Component):
    """Importer the WooCommerce Product"""

    _name = "woo.product.product.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.product.product"

    def _after_import(self, binding, **kwargs):
        """
        This method is Overrides the default behavior of _after_import when importing
        images from a remote record. If no image records are found in the remote record,
        it returns the result of the super class's '_after_import' method.
        """
        result = super(WooProductProductImporter, self)._after_import(binding, **kwargs)
        image_record = self.remote_record.get("images")
        if not image_record:
            return result
        image_importer = self.component(usage="product.image.importer")
        image_importer.run(self.external_id, binding, image_record)
        return result
