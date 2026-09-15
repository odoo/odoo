from odoo.tools.module_data import rename_in_stored_expressions


def migrate(cr, version):
    if not version:
        return
    # ir.cron's code lives on its delegated ir.actions.server record. Include
    # custom actions that call the credential model from another model's action.
    rename_in_stored_expressions(
        cr,
        "cron_validate_credentials",
        "_cron_probe_credentials",
        unique=True,
    )
