from odoo.tools.module_data import adopt_xmlids


def migrate(cr, version):
    adopt_xmlids(
        cr,
        "product_asset",
        "resource_asset",
        ["field_resource_asset__odometer_uom_name"],
    )
