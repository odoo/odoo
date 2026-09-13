from odoo import models

from .automation_rule import get_webhook_request_payload


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    def _prepare_eval_context(self, action):
        eval_context = super()._prepare_eval_context(action)
        if action.state == "code":
            payload = self.env.context.get("webhook_payload")
            if payload is None:
                payload = get_webhook_request_payload()
            if payload is not None:
                eval_context["payload"] = payload
        return eval_context
