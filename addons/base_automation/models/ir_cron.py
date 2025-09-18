from odoo import models


class IrCron(models.Model):
    _inherit = "ir.cron"

    def action_open_automation(self):
        return self.ir_actions_server_id.action_open_automation()
