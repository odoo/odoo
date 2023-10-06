# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.http import route
from odoo.addons.web.controllers.home import Home

class EventSharePostHomeController(Home):
    @route()
    def robots(self, **kwargs):
        """Allow crawlers to visit the routes of this module to generate embeds."""
        robots_res = super().robots(**kwargs)
        return "User-agent: *\nAllow: /social_share/\n\n" + robots_res.get_data(as_text=True)
