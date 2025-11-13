from odoo import models, fields
from odoo.tools import SQL
import re


class WebsiteTechnicalPage(models.Model):
    """
    This model allows listing technical pages whose route decorator is marked
    thanks to the `list_as_website_content` option.
    """
    _name = "website.technical.page"
    _description = "Website Technical Page"
    _auto = False

    name = fields.Char("Page Name")
    website_url = fields.Char("Website Page URL")

    def open_website_url(self):
        """
        Opens the technical page for the given URL and website.
        """
        return self.env["website"].get_client_action(self.website_url)

    # We removed the `@ormcache("routing")` here because `list_as_website_content`
    # can be defined as a callable for shop/extra_info route. when toggling the "Extra Info"
    # page option, this attribute calls a method and the available
    # routes need to be recomputed immediately. Keeping the cache would prevent
    # the updated route list from being reflected without restarting the server.
    def _get_static_routes(self):
        """
        Returns a set of website content static routes.
        """
        dynamic_route_re = re.compile(r"<[^>]+>")
        routes = set()
        for rule in self.env["ir.http"].routing_map().iter_rules():
            endpoint = rule.endpoint.routing
            route_title = endpoint.get("list_as_website_content")
            if callable(route_title):
                route_title = route_title(self.env)
            if route_title:
                last_static_route = next(
                    r for r in reversed(endpoint.get("routes", []))
                    if not dynamic_route_re.search(r)
                )
                routes.add((str(route_title), last_static_route))
        return routes

    @property
    def _table_query(self):
        routes = self._get_static_routes()
        values = ", ".join(str(route) for route in routes)

        return SQL("""
            SELECT row_number() OVER (ORDER BY UPPER(column1) ASC) AS id,
                column1 AS name,
                column2 AS website_url
            FROM (VALUES %s) AS t(column1, column2)
        """ % values)
