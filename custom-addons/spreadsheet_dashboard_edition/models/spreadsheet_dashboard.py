from odoo import api, fields, models, _


class SpreadsheetDashboard(models.Model):
    _name = 'spreadsheet.dashboard'
    _inherit = ['spreadsheet.dashboard', 'spreadsheet.mixin']

    file_name = fields.Char(compute='_compute_file_name')

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
        snapshot = data["data"]
        revisions = data["revisions"]
        update_locale_command = {
            "type": "UPDATE_LOCALE",
            "locale": self.env["res.lang"]._get_user_spreadsheet_locale(),
        }
        revisions.append(self._build_new_revision_data(update_locale_command))
        return {
            "snapshot": snapshot,
            "revisions": revisions,
            "default_currency": data["default_currency"],
        }

    @api.depends("name")
    def _compute_file_name(self):
        for dashboard in self:
            dashboard.file_name = f"{dashboard.name}.osheet.json"

    def action_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_edit_dashboard',
            'params': {
                'spreadsheet_id': self.id,
            }
        }

    def _creation_msg(self):
        return _("New dashboard created")
