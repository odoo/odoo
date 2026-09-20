from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "product_combo_item", ["company_id"])
    schema.drop_columns(cr, "product_template_attribute_value", ["product_tmpl_id"])
