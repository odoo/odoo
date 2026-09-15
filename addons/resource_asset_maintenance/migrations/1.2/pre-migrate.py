from odoo.tools.module_data import adopt_xmlids

RENAMED_XMLIDS = {
    "maintenance_request_view_form_asset": "maintenance_order_view_form_asset",
    "maintenance_request_view_search_asset": "maintenance_order_view_search_asset",
}


def migrate(cr, version):
    if not version:
        return
    adopt_xmlids(
        cr,
        "resource_asset_maintenance",
        "resource_asset_maintenance",
        (),
        renamed=RENAMED_XMLIDS,
    )
