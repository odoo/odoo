from odoo.tools.module_data import adopt_xmlids


def migrate(cr, version):
    # The ledger's odometer reading is core's now. Adopting it here, before
    # either module loads, is what keeps `product_asset` from leaving an
    # orphaned xmlid for `_process_end` to reap.
    adopt_xmlids(
        cr,
        "product_asset",
        "resource_asset_product",
        ["field_resource_asset_log__odometer"],
    )
