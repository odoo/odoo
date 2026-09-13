from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref(
        "automation.ir_cron_data_automation_resume", raise_if_not_found=False
    )
    if cron:
        cron.write(
            {
                "name": "Automation Rules: run due workflow steps",
                "code": "model._dispatch_due_steps()",
            }
        )
