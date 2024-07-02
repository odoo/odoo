from odoo.http import route

from odoo.addons.web.controllers.home import Home

class HomeController(Home):
    @route()
    def robots(self, **kwargs):
        """Allow crawlers to visit the routes of this module to generate embeds."""
        robots_res = super().robots(**kwargs)
        allow_string = "User-agent: *\nAllow: /cards/"
        return allow_string + robots_res.get_data(as_text=True)
