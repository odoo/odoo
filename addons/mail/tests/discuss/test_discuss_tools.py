# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, route
from odoo.tests import HttpCase, new_test_user, tagged

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import bus_rpc


@tagged("post_install", "-at_install")
class TestDiscussTools(MailCommon, HttpCase):
    def test_bus_rpc(self):
        class Dummycontroller(Controller):
            @route("/bus/foo", type="jsonrpc", auth="public")
            @bus_rpc
            def bus_foo(self):
                pass

        self.env.registry.clear_cache("routing")
        self.addCleanup(self.env.registry.clear_cache, "routing")
        bob_user = new_test_user(self.env, "bob_user")
        self.authenticate("bob_user", "bob_user")
        self._reset_bus()
        self.assertFalse(self.env["bus.bus"].search([]))
        with self.assertBus(
            [[self.env.cr.dbname, "res.partner", bob_user.partner_id.id]],
            [{"type": "bus_rpc/end", "payload": "foo"}],
        ):
            self.make_jsonrpc_request("/bus/foo", {"bus_rpc_uuid": "foo"})
