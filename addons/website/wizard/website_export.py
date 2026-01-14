# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteExportWizard(models.TransientModel):
    _name = "website.export.wizard"
    _description = "Website Export Wizard"

    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        default=lambda self: self.env["website"].get_current_website(),
    )
    page_scope = fields.Selection(
        [
            ("all", "All Pages"),
            ("selection", "Selected Pages"),
        ],
        string="Pages to Export",
        required=True,
        default="all",
    )
    page_ids = fields.Many2many(
        "website.page",
        string="Pages",
        domain="[('website_id', 'in', [website_id, False])]",
    )
    include_assets = fields.Boolean(string="Include Assets", default=True)

    @api.onchange("page_scope")
    def _onchange_page_scope(self):
        if self.page_scope == "all":
            self.page_ids = False

    @api.onchange("website_id")
    def _onchange_website_id(self):
        if self.page_ids:
            self.page_ids = False

    def action_export(self):
        return {"type": "ir.actions.act_window_close"}
