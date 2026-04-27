from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    # Remove xsd validation crons as the validation is done differently.
    env = api.Environment(cr, SUPERUSER_ID, {})
    old_cron = env.ref("l10n_no_saft.ir_cron_load_xsd_file", raise_if_not_found=False)
    old_cron_1_3 = env.ref("l10n_no_saft.ir_cron_load_xsd_file_1_3", raise_if_not_found=False)
    cron_ids = tuple(cron.id for cron in (old_cron, old_cron_1_3) if cron)
    if cron_ids:
        cr.execute(
            "DELETE FROM ir_cron WHERE id in %(cron_ids)s",
            {'cron_ids': cron_ids}
        )
