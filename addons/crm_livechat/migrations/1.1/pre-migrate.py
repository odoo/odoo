from odoo.tools.module_data import rename_field, rename_in_stored_expressions


def migrate(cr, version):
    if not version:
        return
    rename_field(cr, "chatbot.script.step", "crm_team_id", "team_id")
    rename_in_stored_expressions(
        cr, "crm_team_id", "team_id", model="chatbot.script.step"
    )
