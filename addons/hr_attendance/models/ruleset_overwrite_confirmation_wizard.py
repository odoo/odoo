from odoo import models


class RulesetOverwriteConfirmationWizard(models.TransientModel):
    _name = 'ruleset.overwrite.confirmation.wizard'
    _description = 'Confirm Ruleset Overwrite'

    def action_confirm(self):
        active_ids = self.env.context.get('active_ids')
        ruleset_id = self.env.context.get('ruleset_id')
        records = self.env['hr.version'].browse(active_ids)
        records.ruleset_id = ruleset_id
