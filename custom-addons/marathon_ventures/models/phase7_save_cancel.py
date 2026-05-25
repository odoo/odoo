# -*- coding: utf-8 -*-
"""Phase 7 — Explicit Save / Cancel buttons on every mv.* form.

Odoo 19's default UX uses small cloud/X icons in the breadcrumb for Save/Discard.
Users coming from Salesforce expect prominent Save and Cancel buttons in the
header. We add a small mixin that exposes:
  * action_save_record  → no-op (Odoo auto-saves any pending changes when a
    type="object" button is clicked, so just having the button triggers the save).
  * action_cancel_to_list → saves any pending changes and navigates back to the
    model's list view (closest semantic to "Cancel" since Odoo has no
    server-side discard once the record is saved).
"""
from odoo import models, _


class MvSaveButtonMixin(models.AbstractModel):
    _name = 'mv.save.button.mixin'
    _description = 'Mixin exposing Save / Cancel action methods used by mv.* form headers.'

    def action_save_record(self):
        """No-op — clicking the Save button in the form triggers Odoo's
        framework-level save BEFORE invoking this method, which is why the
        method body is intentionally empty.
        """
        return True

    def action_cancel_to_list(self):
        """Saves pending changes and navigates to the model's tree/list view."""
        return {
            'type': 'ir.actions.act_window',
            'name': self._description or self._name,
            'res_model': self._name,
            'view_mode': 'list,form',
            'target': 'current',
        }
