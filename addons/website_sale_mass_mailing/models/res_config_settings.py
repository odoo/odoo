from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_newsletter_enabled = fields.Boolean(
        compute="_compute_is_newsletter_enabled",
        store=True,
        readonly=False,
    )
    newsletter_id = fields.Many2one(
        related="website_id.newsletter_id",
        readonly=False,
    )

    @api.depends("website_id")
    def _compute_is_newsletter_enabled(self):
        for record in self:
            website = record.with_context(website_id=record.website_id.id).website_id
            record.is_newsletter_enabled = website.is_view_active(
                "website_sale_mass_mailing.newsletter"
            )

    def set_values(self):
        super().set_values()
        if self.website_id:
            website = self.with_context(website_id=self.website_id.id).website_id
            website_newsletter_view = website.viewref(
                "website_sale_mass_mailing.newsletter"
            )
            if website_newsletter_view.active != self.is_newsletter_enabled:
                website_newsletter_view.active = self.is_newsletter_enabled
