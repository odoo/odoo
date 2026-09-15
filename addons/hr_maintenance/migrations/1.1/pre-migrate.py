from odoo.tools.module_data import adopt_xmlids

RENAMED_XMLIDS = {
    "maintenance_request_view_form_inherit_hr": "maintenance_order_view_form_inherit_hr",
    "maintenance_request_view_kanban_inherit_hr": "maintenance_order_view_kanban_inherit_hr",
    "maintenance_request_view_search_inherit_hr": "maintenance_order_view_search_inherit_hr",
    "maintenance_request_view_tree_inherit_hr": "maintenance_order_view_list_inherit_hr",
}


def migrate(cr, version):
    if not version:
        return
    adopt_xmlids(cr, "hr_maintenance", "hr_maintenance", (), renamed=RENAMED_XMLIDS)
