import json

from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountReturnSubmissionWizard(models.TransientModel):
    _name = "account.return.submission.wizard"
    _description = "Return submission wizard"

    instructions = fields.Html()
    return_id = fields.Many2one(
        comodel_name="account.return",
        required=True,
    )

    @_debug.perf.timed
    def action_proceed_with_submission(self):
        _debug.lifecycle("action_proceed_with_submission", records=self)
        self.check_singleton()
        return self.return_id._proceed_with_submission()

    @api.model
    def _open_submission_wizard(self, account_return, instructions=None):
        record_action = self.create(
            {
                "instructions": instructions,
                "return_id": account_return.id if account_return else None,
            }
        )._get_records_action(target="new")

        record_action["name"] = _("Submission Instructions")

        record_action.setdefault("context", {})
        record_action["context"] |= {
            "dialog_size": "large",
        }
        return record_action

    def print_pdf(self):
        options = self.return_id._get_closing_report_options()
        return {
            "type": "ir_actions_account_report_download",
            "data": {
                "model": self.env.context.get("model"),
                "options": json.dumps(options),
                "file_generator": "export_to_pdf",
                "no_closing_after_download": True,
            },
        }
