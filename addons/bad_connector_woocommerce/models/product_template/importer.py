import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

# pylint: disable=W7950

_logger = logging.getLogger(__name__)


class WooProductTemplateBatchImporter(Component):
    """Batch Importer the WooCommerce Product Template"""

    _name = "woo.product.template.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.product.template"


class WooProductTemplateImportMapper(Component):
    """Impoter Mapper for the WooCommerce Product Template"""

    _name = "woo.product.template.import.mapper"
    _inherit = "woo.product.common.mapper"
    _apply_on = "woo.product.template"

    @mapping
    def variant_different(self, record):
        """Mapping for variant_different"""
        attributes = record.get("attributes", [])
        variation_count_from_payload = 1

        for attribute in attributes:
            if not attribute.get("variation"):
                continue
            options = attribute.get("options")
            if not options:
                continue
            variation_count_from_payload *= len(options)

        return {
            "variant_different": variation_count_from_payload
            != len(record.get("variations", []))
        }

    def _prepare_attribute_line(self, attribute, value_ids):
        """Prepare an attribute line."""
        attribute_line = {
            "attribute_id": attribute.id,
            "value_ids": [(6, 0, value_ids)],
        }
        return attribute_line

    def _get_attribute_lines(self, map_record):
        """Get all attribute lines for the product."""
        attribute_lines = []
        attribute_binder = self.binder_for("woo.product.attribute")
        template_binder = self.binder_for("woo.product.template")

        record = map_record.source

        for woo_attribute in record.get("attributes", []):
            woo_attribute_id = woo_attribute.get("id", 0)
            woo_attribute_id = (
                self._get_attribute_id_format(woo_attribute, record)
                if woo_attribute_id == 0
                else woo_attribute_id
            )

            attribute = attribute_binder.to_internal(woo_attribute_id, unwrap=True)
            product_template = template_binder.to_internal(
                record.get("id"), unwrap=True
            )

            # Check if the attribute line already exists for the product_template.
            existing_attribute_line = product_template.attribute_line_ids.filtered(
                lambda line: line.attribute_id.id == attribute.id
            )

            value_ids = [
                value.id
                for option in woo_attribute.get("options", [])
                for value in attribute.value_ids.filtered(lambda v: v.name == option)
            ]

            # If the attribute line already exists, update it.
            if existing_attribute_line:
                existing_attribute_line.write({"value_ids": [(6, 0, value_ids)]})
            # Otherwise, create a new attribute line.
            else:
                attribute_line = self._prepare_attribute_line(attribute, value_ids)
                attribute_lines.append((0, 0, attribute_line))

        return attribute_lines

    def finalize(self, map_record, values):
        """Override the finalize method to add attribute lines to the product."""
        attribute_lines = self._get_attribute_lines(map_record)
        values.update({"attribute_line_ids": attribute_lines})
        return super(WooProductTemplateImportMapper, self).finalize(map_record, values)


class WooProductTemplateImporter(Component):
    """Importer the WooCommerce Product Template"""

    _name = "woo.product.template.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.product.template"

    def _after_import(self, binding, **kwargs):
        """Inherit Method: inherit method to import remote child products"""
        result = super(WooProductTemplateImporter, self)._after_import(
            binding, **kwargs
        )
        variant_ids = self.remote_record.get("variations")
        product_model = self.env["woo.product.product"]
        for variant_id in variant_ids:
            job_options = {}
            description = self.backend_record.get_queue_job_description(
                prefix=product_model.import_record.__doc__ or "Record Import Of",
                model=product_model._description,
            )
            job_options["description"] = description
            delayable = product_model.with_company(
                binding.backend_id.company_id
            ).with_delay(**job_options or {})
            delayable.import_record(
                backend=self.backend_record, external_id=variant_id, **kwargs
            )
        return result
