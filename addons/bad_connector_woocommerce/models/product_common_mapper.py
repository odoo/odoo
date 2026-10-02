from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError


class ProductCommonImportMapper(Component):
    _name = "woo.product.common.mapper"
    _inherit = "woo.import.mapper"

    def is_product_type_variation(self, record):
        """Check if the product type is 'variation' and return True,
        otherwise return False."""
        return record.get("type") == "variation"

    @mapping
    def name(self, record):
        """Mapping for Name"""
        if self.is_product_type_variation(record):
            return {}
        name = record.get("name")
        if not name:
            raise MappingError(
                _("Product Template name doesn't exist for Product ID %s Please check")
                % record.get("id")
            )
        return {"name": name}

    @mapping
    def description(self, record):
        """Mapping for description"""
        if self.is_product_type_variation(record):
            return {}
        description = record.get("description")
        return {"description": description} if description else {}

    @mapping
    def purchase_ok(self, record):
        """Mapping for purchase_ok"""
        if self.is_product_type_variation(record):
            return {}
        return {"purchase_ok": record.get("purchasable", False)}

    @mapping
    def categ_id(self, record):
        """Mapping for Product category"""
        if self.is_product_type_variation(record):
            return {}
        category_id = self.backend_record.product_categ_id.id
        binder = self.binder_for("woo.product.category")
        for category in record.get("categories", []):
            woo_binding = binder.to_internal(category.get("id"))
            if woo_binding and woo_binding.odoo_id:
                category_id = woo_binding.odoo_id.id
                break
        return {"categ_id": category_id}

    @mapping
    def woo_product_categ_ids(self, record):
        """Mapping for woo_product_categ_ids"""
        if self.is_product_type_variation(record):
            return {}
        category_ids = []
        woo_product_categories = record.get("categories", [])
        binder = self.binder_for("woo.product.category")
        for category in woo_product_categories:
            woo_binding = binder.to_internal(category.get("id"))
            if not woo_binding:
                continue
            category_ids.append(woo_binding.id)
        return {"woo_product_categ_ids": [(6, 0, category_ids)]} if category_ids else {}

    @only_create
    @mapping
    def detailed_type(self, record):
        """Mapping for detailed_type"""
        if self.is_product_type_variation(record):
            return {}
        if record.get("downloadable"):
            return {"detailed_type": "service"}
        return {
            "detailed_type": "product"
            if record.get("manage_stock")
            else self.backend_record.default_product_type
        }

    @mapping
    def product_tag_ids(self, record):
        """Mapping for product_tag_ids"""
        if self.is_product_type_variation(record):
            return {}
        tag_ids = []
        tags = record.get("tags", [])
        binder = self.binder_for("woo.product.tag")
        for tag in tags:
            product_tag = binder.to_internal(tag.get("id"), unwrap=True)
            if not product_tag:
                continue
            tag_ids.append(product_tag.id)
        return {"product_tag_ids": [(6, 0, tag_ids)]} if tag_ids else {}

    def _get_attribute_id_format(self, attribute, record, option=None):
        """Return the attribute and attribute value's unique id"""
        if not option:
            return "{}-{}".format(attribute.get("name"), record.get("id"))
        return "{}-{}-{}".format(option, attribute.get("id"), record.get("id"))

    def _get_product_attribute(self, attribute_id, record):
        """Get the product attribute that contains id as zero"""
        binder = self.binder_for("woo.product.attribute")
        created_id = self._get_attribute_id_format(attribute_id, record)
        product_attribute = binder.to_internal(created_id)
        if not product_attribute and not attribute_id.get("id"):
            product_attribute = self.env["woo.product.attribute"].create(
                {
                    "name": attribute_id.get("name"),
                    "backend_id": self.backend_record.id,
                    "external_id": created_id,
                    "not_real": True,
                }
            )
        return product_attribute

    def _create_attribute_values(self, options, product_attribute, attribute, record):
        """Create attribute value binding that doesn't contain ids"""
        binder = self.binder_for("woo.product.attribute.value")
        for option in options:
            created_id = self._get_attribute_id_format(attribute, record, option)
            product_attribute_value = binder.to_internal(created_id)
            if not product_attribute_value:
                attribute_id = self._get_attribute_id_format(attribute, record)
                binder = self.binder_for("woo.product.attribute")
                product_attr = binder.to_internal(attribute_id, unwrap=True)
                attribute_value = self.env["product.attribute.value"].search(
                    [
                        ("name", "=", option),
                        ("attribute_id", "=", product_attr.id),
                    ],
                    limit=1,
                )
                self.env["woo.product.attribute.value"].create(
                    {
                        "name": option,
                        "attribute_id": product_attribute.odoo_id.id,
                        "woo_attribute_id": product_attribute.id,
                        "backend_id": self.backend_record.id,
                        "external_id": created_id,
                        "odoo_id": attribute_value.id if attribute_value else None,
                    }
                )
        return True

    @mapping
    def woo_attribute_ids(self, record):
        """Mapping of woo_attribute_ids"""
        if self.is_product_type_variation(record):
            return {}
        attribute_ids = []
        woo_product_attributes = record.get("attributes", [])
        if not woo_product_attributes:
            return {}
        binder = self.binder_for("woo.product.attribute")
        for attribute in woo_product_attributes:
            attribute_id = attribute.get("id")
            woo_binding = binder.to_internal(attribute_id)
            if woo_binding:
                attribute_ids.append(woo_binding.id)
                continue
            product_attribute = self._get_product_attribute(attribute, record)
            options = attribute.get("options") or [attribute.get("option")]
            self._create_attribute_values(options, product_attribute, attribute, record)
            attribute_ids.append(product_attribute.id)
        return {"woo_attribute_ids": [(6, 0, attribute_ids)]}

    @mapping
    def woo_product_attribute_value_ids(self, record):
        """Mapping for woo_product_attribute_value_ids"""
        if self.is_product_type_variation(record):
            return {}
        attribute_value_ids = []
        woo_attributes = record.get("attributes", [])
        binder = self.binder_for("woo.product.attribute")
        for woo_attribute in woo_attributes:
            attribute_id = woo_attribute.get("id")
            if attribute_id == 0:
                attribute_id = self._get_attribute_id_format(woo_attribute, record)
            attribute = binder.to_internal(attribute_id, unwrap=True)
            options = woo_attribute.get("options") or [woo_attribute.get("option")]
            for option in options:
                attribute_value = self.env["woo.product.attribute.value"].search(
                    [
                        ("name", "=", option),
                        ("attribute_id", "=", attribute.id),
                    ],
                    limit=1,
                )
                if not attribute_value:
                    raise MappingError(
                        _("'%s' attribute value not found!Import Attribute first.")
                        % option
                    )
                attribute_value_ids.append(attribute_value.id)
        return {"woo_product_attribute_value_ids": [(6, 0, attribute_value_ids)]}

    @mapping
    def list_price(self, record):
        """Mapping product Price"""
        if self.is_product_type_variation(record):
            return {}
        return {"list_price": record.get("price")}

    @mapping
    def default_code(self, record):
        """Mapped product default code."""
        default_code = record.get("sku")
        if not default_code and not self.backend_record.without_sku:
            raise MappingError(
                _("SKU is Missing for the product '%s' !", record.get("name"))
            )
        return {"default_code": default_code} if default_code else {}
