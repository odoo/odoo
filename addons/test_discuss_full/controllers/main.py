# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, route
from odoo.addons.mail.tools.guard_discuss_access import guard_discuss_access


class TestDiscussController(Controller):
    @route("/test_discuss_full/guarded_route_test", type="json", auth="public", cors="*")
    @guard_discuss_access
    def guarded_route(self):
        return "OK"
