from odoo import models
from odoo.tools.safe_eval import safe_eval


class SuiteDashboardProvider(models.AbstractModel):
    _name = "suite.dashboard.provider"
    _description = "Dashboard Provider Contract"

    def _get_widget_definitions(self):
        return []

    def _get_widget_payload(self, widget_key, filters):
        raise NotImplementedError()

    def _get_drilldown_action(self, widget_key, filters):
        return False

    def _get_quick_access_actions(self, filters):
        return []

    def _get_ai_context(self, widget_keys, filters):
        return {}

    def _resolve_window_action(self, xmlid):
        try:
            return self.env["ir.actions.actions"]._for_xml_id(xmlid)
        except ValueError:
            return False

    def _action_for_xmlid(self, xmlid, domain=None, context=None, name=None):
        action = self._resolve_window_action(xmlid)
        if not action:
            return False
        if domain is not None:
            action["domain"] = domain
        if context:
            existing_context = action.get("context") or {}
            if isinstance(existing_context, str):
                existing_context = safe_eval(existing_context, {"uid": self.env.uid})
            if not isinstance(existing_context, dict):
                existing_context = {}
            action["context"] = {**existing_context, **context}
        if name:
            action["name"] = name
        return action
