from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    website_id = fields.Many2one(
        comodel_name="website",
        compute="_compute_website_id",
        store=True,
    )

    def _compute_website_id(self):
        websites_by_company = (
            self.env["website"]
            .search([("company_id", "in", self.ids)])
            .grouped("company_id")
        )
        for company in self:
            company.website_id = websites_by_company.get(company, self.env["website"])[
                :1
            ]

    @api.model
    def action_view_website_theme_selector(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website.theme_install_kanban_action"
        )
        action["target"] = "new"
        return action

    @api.constrains("active")
    def _check_active(self):
        super()._check_active()
        for company in self:
            if not company.active and company.website_id:
                _debug.logic(
                    "company_archive_refused",
                    reason="has_website",
                    company=company.id,
                    website=company.website_id.id,
                )
                raise ValidationError(
                    _(
                        "The company “%(company_name)s” cannot be archived because it has a linked website “%(website_name)s”."
                        "\nChange that website's company first.",
                        company_name=company.name,
                        website_name=company.website_id.name,
                    )
                )

    def google_map_img(self, zoom=8, width=298, height=298):
        partner = self.sudo().partner_id
        return (partner and partner.google_map_img(zoom, width, height)) or None

    def google_map_link(self, zoom=8):
        partner = self.sudo().partner_id
        return (partner and partner.google_map_link(zoom)) or None
