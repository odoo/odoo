from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Remove the old unit UI before the unit_id field/model disappears from the registry.
    for xmlid_name in (
        "menu_sifnext_unit",
        "action_sifnext_unit",
        "view_users_form_sifnext_unit",
        "view_sifnext_unit_list",
        "view_sifnext_unit_form",
        "unit_company_rule",
        "access_sifnext_unit_user",
        "access_sifnext_unit_finance",
    ):
        record = env.ref("sifnext_ppl.%s" % xmlid_name, raise_if_not_found=False)
        if record and record.exists():
            record.unlink()
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = 'sifnext_ppl' AND name = %s",
            (xmlid_name,),
        )
