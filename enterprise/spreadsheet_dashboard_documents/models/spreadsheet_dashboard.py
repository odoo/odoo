from odoo import _, api, models


class SpreadsheetDashboard(models.Model):
    _name = 'spreadsheet.dashboard'
    _inherit = ['spreadsheet.dashboard']

    def action_add_document_spreadsheet_to_dashboard(self):
        return {
            "type": "ir.actions.client",
            "tag": "action_dashboard_add_spreadsheet",
            "params": {
                "dashboardGroupId": self.env.context.get("dashboard_group_id"),
            },
        }

    @api.model
    def add_document_spreadsheet_to_dashboard(self, dashboard_group_id, document_id):
        document = self.env["documents.document"].browse(document_id)
        dashboard = self.create({
            "name": document.name,
            "dashboard_group_id": dashboard_group_id,
            "spreadsheet_snapshot": document.spreadsheet_snapshot,
            "spreadsheet_binary_data": document.datas,
        })
        document._copy_revisions_to(dashboard)
        dashboard._delete_comments_from_data()

    @api.model
    def action_open_new_dashboard(self, dashboard_group_id):
        dashboard = self.create({
            "name": _("Untitled dashboard"),
            "dashboard_group_id": dashboard_group_id,
        })
        return {
            "type": "ir.actions.client",
            "tag": "action_edit_dashboard",
            "params": {
                "spreadsheet_id": dashboard.id,
            },
        }
