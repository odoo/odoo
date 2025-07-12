from odoo import models, fields
import re


class WebsiteTechnicalPage(models.TransientModel):
    """
    Transient model to list editable technical website pages.
    """
    _name = "website.technical.page"
    _description = "Website Technical Page"

    name = fields.Char("Page Name")
    website_url = fields.Char("Website Page URL")

    def open_website_url(self):
        """
        Opens the technical page for given URL and website.
        """
        return self.env["website"].get_client_action(self.website_url)

    def load_technical_pages(self, *args, **kwargs):
        """
        Load static public website routes with list_as_editable_page=True.
        """
        TechnicalPage = self.env["website.technical.page"]
        existing_routes = TechnicalPage.search([]).mapped("website_url")
        dynamic_route_re = re.compile(r"<[^>]+>")
        records_to_create = []

        for rule in self.env["ir.http"].routing_map().iter_rules():
            if rule.endpoint.routing.get("list_as_editable_page"):
                for route in rule.endpoint.routing.get("routes", []):
                    if (
                        dynamic_route_re.search(route)
                        or route in existing_routes
                    ):
                        continue

                    records_to_create.append({
                        "name": " > ".join([name.capitalize() for name in route.strip("/").split("/")]) or "Home",
                        "website_url": route,
                    })
                    existing_routes.append(route)
        if records_to_create:
            TechnicalPage.create(records_to_create)

        return {
            "type": "ir.actions.act_window",
            "name": "Technical Pages",
            "res_model": "website.technical.page",
            "view_mode": "list",
            "target": "current",
        }
