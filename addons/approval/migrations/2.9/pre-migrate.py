from odoo.db.schema import table_exists
from odoo.tools.module_data import adopt_xmlids, rename_model

RENAMED_XMLIDS = {
    "access_approval_binding_observation": "access_approval_observation",
}


def migrate(cr, version):
    if not version:
        return
    if table_exists(cr, "approval_binding_observation"):
        rename_model(cr, "approval.binding.observation", "approval.observation")
    adopt_xmlids(cr, "approval", "approval", (), renamed=RENAMED_XMLIDS)
