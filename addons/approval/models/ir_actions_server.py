from odoo import models

from . import approval_trace as trace


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    def _gate_run(self, records, run, replayable=True):
        """Consult approval bindings before running, on the server.

        web_studio gated a server action only in the browser: the client asked for
        approval before executing, so any RPC caller ran the action unchecked. The
        gate here holds for every caller -- `run()` and an AI agent's tool call
        alike -- with the records the action targets as its subject, and the
        caller's elevation measured on this environment before the action itself
        switches to sudo.
        """
        self.check_singleton()
        Binding = self.env["approval.binding"]
        if not Binding._enabled():
            return super()._gate_run(records, run, replayable)
        bindings = Binding._bindings_for_action(self.id)
        trace.BINDING.event(
            "action_run",
            action=self.id,
            bindings=bindings.ids,
            records=records.ids if bindings else None,
        )
        if not bindings or not records:
            return super()._gate_run(records, run, replayable)
        return Binding._gate(records, bindings, self.name, run, replayable=replayable)
