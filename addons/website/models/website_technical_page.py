from odoo import models, fields
from odoo.tools import ormcache, SQL
import re


class WebsiteTechnicalPage(models.Model):
    """
    This model to  use list technical website pages.
    """
    _name = "website.technical.page"
    _description = "Website Technical Page"
    _auto = False

    name = fields.Char("Page Name")
    website_url = fields.Char("Website Page URL")

    def open_website_url(self):
        """
        Opens the technical page for given URL and website.
        """
        return self.env["website"].get_client_action(self.website_url)

    @ormcache()
    def get_static_routes(self):
        """
        Return a set of website content static routes.
        """
        dynamic_route_re = re.compile(r"<[^>]+>")
        routes = set()
        for rule in self.env["ir.http"].routing_map().iter_rules():
            endpoint = rule.endpoint.routing
            route_title = endpoint.get("list_as_website_content")
            if route_title:
                last_static_route = next(
                    r for r in reversed(endpoint.get("routes", []))
                    if not dynamic_route_re.search(r)
                )
                routes.add((str(route_title), last_static_route))
        return routes

    @property
    def _table_query(self):
        routes = self.get_static_routes()
        values = ", ".join(str(route) for route in routes)

        return SQL("""
            SELECT row_number() OVER () AS id,
                    column1 AS name,
                    column2 AS website_url
            FROM (VALUES %s) AS t(column1, column2)
        """ % values)
