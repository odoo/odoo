from odoo import api, models, _


class SpreadsheetDashboard(models.Model):
    _name = 'spreadsheet.dashboard'
    _inherit = ['spreadsheet.dashboard', 'spreadsheet.mixin']

    def join_spreadsheet_session(self, *args, **kwargs):
        return dict(
            super().join_spreadsheet_session(*args, **kwargs),
            is_published=self.is_published
        )

    def action_edit_dashboard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "action_edit_dashboard",
            "params": {
                "spreadsheet_id": self.id,
            },
        }

    def get_readonly_dashboard(self):
        self.ensure_one()
        data = self.join_spreadsheet_session()
        if self._dashboard_is_empty() and self.sample_dashboard_file_path:
            sample_data = self._get_sample_dashboard()
            if sample_data:
                return {
                    "snapshot": sample_data,
                    "is_sample": True,
                }
        update_locale_command = {
            "type": "UPDATE_LOCALE",
            "locale": self.env["res.lang"]._get_user_spreadsheet_locale(),
        }
        snapshot = data["data"]
        revisions = data["revisions"]
        revisions.append(self._build_new_revision_data([update_locale_command]))
        return {
            "snapshot": snapshot,
            "revisions": revisions,
            "default_currency": data["default_currency"],
        }

    def _dashboard_is_empty(self):
        self._check_collaborative_spreadsheet_access("read")
        all_revisions = self.sudo().with_context(active_test=False).spreadsheet_revision_ids
        return not len(all_revisions) and super()._dashboard_is_empty()

    def action_open_spreadsheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_edit_dashboard',
            'params': {
                'spreadsheet_id': self.id,
            }
        }

    @api.model
    def _get_spreadsheet_selector(self):
        if self.env.user.has_group('spreadsheet_dashboard.group_dashboard_manager'):
            return {
                "model": self._name,
                "display_name": _("Dashboards"),
                "sequence": 10,
                "allow_create": False,
            }
