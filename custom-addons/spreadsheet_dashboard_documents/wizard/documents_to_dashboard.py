# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json


from odoo import api, fields, models


class DocumentsToDashboardWizard(models.TransientModel):
    _name = "spreadsheet.document.to.dashboard"
    _description = "Create a dashboard from a spreadsheet document"

    name = fields.Char(
        "Dashboard Name",
        required=True,
        compute="_compute_name",
        store=True,
        readonly=False,
        precompute=True,
    )
    document_id = fields.Many2one(
        "documents.document",
        readonly=True,
        required=True,
        domain=[("handler", "=", "spreadsheet")],
    )
    dashboard_group_id = fields.Many2one("spreadsheet.dashboard.group", string="Dashboard Section", required=True)
    group_ids = fields.Many2many(
        "res.groups", default=lambda self: self._default_group_ids(), string="Access Groups"
    )

    def _default_group_ids(self):
        return self.env["spreadsheet.dashboard"].default_get(["group_ids"])["group_ids"]

    @api.depends("document_id.name")
    def _compute_name(self):
        for wizard in self:
            wizard.name = wizard.document_id.name

    def create_dashboard(self):
        self.ensure_one()
        spreadsheet_data = self.document_id._get_spreadsheet_snapshot()
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": self.name,
                "dashboard_group_id": self.dashboard_group_id.id,
                "group_ids": self.group_ids.ids,
                "spreadsheet_data": json.dumps(spreadsheet_data),
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_dashboard",
            "name": self.name,
            "params": {
                "dashboard_id": dashboard.id,
            },
        }
