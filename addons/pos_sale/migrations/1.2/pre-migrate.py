from odoo.tools.module_data import rename_field, rename_in_stored_expressions

RENAMES = (
    ("pos.config", "crm_team_id", "team_id"),
    ("pos.order", "crm_team_id", "team_id"),
    ("pos.session", "crm_team_id", "team_id"),
    ("res.config.settings", "pos_crm_team_id", "pos_team_id"),
)


def migrate(cr, version):
    if not version:
        return
    for model, old, new in RENAMES:
        rename_field(cr, model, old, new)
        rename_in_stored_expressions(cr, old, new, model=model)
