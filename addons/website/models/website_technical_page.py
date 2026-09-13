import re

from odoo import fields, models
from odoo.tools import SQL, ormcache


class WebsiteTechnicalPage(models.Model):
    _name = "website.technical.page"
    _description = "Website Technical Page"
    _auto = False

    name = fields.Char(string="Page Name")
    website_url = fields.Char(string="Website Page URL")

    def open_website_url(self):
        return self.env["website"].get_client_action(self.website_url)

    @ormcache(cache="routing")
    def get_static_routes(self):
        dynamic_route_re = re.compile(r"<[^>]+>")
        routes = set()
        for rule in self.env["ir.http"].routing_map().iter_rules():
            endpoint = rule.endpoint.routing
            route_title = endpoint.get("list_as_website_content")
            if route_title:
                last_static_route = next(
                    r
                    for r in reversed(endpoint.get("routes", []))
                    if not dynamic_route_re.search(r)
                )
                routes.add((str(route_title), last_static_route))
        return routes

    @property
    def _table_query(self):
        routes = self.get_static_routes()
        if not routes:
            return SQL(
                "SELECT NULL::int AS id, NULL::text AS name, "
                "NULL::text AS website_url WHERE FALSE"
            )
        values = SQL(", ").join(
            SQL("(%s, %s)", route_title, route_path)
            for route_title, route_path in routes
        )

        return SQL(
            """
            SELECT row_number() OVER () AS id,
                column1 AS name,
                column2 AS website_url
            FROM (VALUES %s) AS t(column1, column2)
        """,
            values,
        )
