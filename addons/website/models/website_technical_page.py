from odoo import models, fields
import re


class WebsiteTechnicalPage(models.TransientModel):
    """
    Model to manage technical website pages in Odoo,
    capturing specific/technical with Editable and route URLs with relevant view and website associations.
    """
    _name = "website.technical.page"
    _description = "Website Technical Page"

    route_url_name = fields.Char(
        "Name Of Url",
        help="The name of the pag, This is used to identify the page in the website."
    )
    route_url = fields.Char(
        "Website URL Path",
        help="The full relative URL to access that pages directly."
    )

    def open_website_url(self):
        """
        Opens the technical page in the frontend website, based on the URL and website.
        """
        return self.env["website"].get_client_action(self.route_url)

    def Import_static_url(self, *args, **kwargs):
        """
        Import static public frontend routes (list_as_editable_page=True),
        excluding CMS pages and already tracked technical pages.
        """
        TechnicalPage = self.env["website.technical.page"].sudo()
        existing_paths_urls = set(TechnicalPage.search([]).mapped("route_url"))
        dynamic_route_filtered = re.compile(r"<[^>]+>")
        web_pages = self.env["website.page"].sudo()

        for rule in self.env["ir.http"].routing_map().iter_rules():
            if rule.endpoint.routing.get("list_as_editable_page"):
                for route in rule.endpoint.routing.get("routes", []):
                    if (dynamic_route_filtered.search(route)
                            or route in existing_paths_urls
                            or web_pages.search([("url", "=", route)])):
                        continue

                    TechnicalPage.create({
                        "route_url_name": route.strip("/").replace("-", " ").capitalize() or "Home",
                        "route_url": route,
                    })
                    existing_paths_urls.add(route)

        return {
            "type": "ir.actions.act_window",
            "name": "Technical Routes",
            "res_model": "website.technical.page",
            "view_mode": "list",
            "target": "current",
        }
