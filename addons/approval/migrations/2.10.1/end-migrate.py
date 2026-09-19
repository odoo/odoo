from odoo import SUPERUSER_ID, api
from odoo.db import schema

PROJECTED = {
    "approval_state": "approval_request_id.state",
    "date_approval_granted": "approval_request_id.date_approval_granted",
    "date_approval_requested": "approval_request_id.date_confirmed",
}


def migrate(cr, version):
    if not version:
        return
    # mixin.approval no longer stores these; its tables belong to models loaded after
    # this module, so they are read off the registry once everything is loaded
    env = api.Environment(cr, SUPERUSER_ID, {})
    for model in env.values():
        if model._abstract or not model._auto:
            continue
        orphans = [
            name
            for name, related in PROJECTED.items()
            if (field := model._fields.get(name)) is not None
            and field.related == related
            and not field.store
        ]
        if orphans:
            schema.drop_columns(cr, model._table, orphans)
