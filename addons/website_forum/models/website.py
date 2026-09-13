from odoo import _, api, fields, models


class Website(models.Model):
    _inherit = "website"

    forum_count = fields.Integer(
        default=0,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        websites = super().create(vals_list)
        websites._update_forum_count()
        return websites

    def get_suggested_controllers(self):
        suggested_controllers = super().get_suggested_controllers()
        suggested_controllers.append(
            (_("Forum"), self.env["ir.http"]._url_for("/forum"), "website_forum")
        )
        return suggested_controllers

    def configurator_get_footer_links(self):
        links = super().configurator_get_footer_links()
        links.append({"text": _("Forum"), "href": "/forum"})
        return links

    def configurator_set_menu_links(self, menu_company, module_data):
        forum_menu = self.env["website.menu"].search(
            [("url", "=", "/forum"), ("website_id", "=", self.id)]
        )
        forum_menu.unlink()
        super().configurator_set_menu_links(menu_company, module_data)

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ["forums", "forums_only", "all"]:
            result.append(
                self.env["forum.forum"]._search_get_detail(self, order, options)
            )
        if search_type in ["forums", "forum_posts_only", "all"]:
            result.append(
                self.env["forum.post"]._search_get_detail(self, order, options)
            )
        if search_type in ["forums", "forum_tags_only", "all"]:
            result.append(
                self.env["forum.tag"]._search_get_detail(self, order, options)
            )
        return result

    def _update_forum_count(self):
        websites = self or self.search([])
        forums_all = self.env["forum.forum"].search([])
        for website in websites:
            website.forum_count = len(
                forums_all.filtered_domain(website.website_domain())
            )
