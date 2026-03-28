from odoo import api, models


class ThemeUtils(models.AbstractModel):
    _inherit = "theme.utils"

    @api.model
    def _theme_semsa_post_copy(self, mod):
        website_id = self.env.context.get("website_id")
        website = website_id and self.env["website"].browse(website_id) or self.env["website"].get_current_website()
        if not website:
            return False

        homepage_view = self.env["ir.ui.view"].with_context(active_test=False).search(
            [
                ("key", "=", "theme_semsa.homepage"),
                ("website_id", "=", website.id),
            ],
            limit=1,
        )
        homepage_page = self.env["website.page"].with_context(active_test=False).search(
            [
                ("website_id", "=", website.id),
                ("url", "=", website.homepage_url or "/"),
            ],
            limit=1,
        )

        if homepage_view and homepage_page and homepage_page.view_id != homepage_view:
            homepage_page.write({"view_id": homepage_view.id})
        return bool(homepage_view)
