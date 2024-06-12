# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class TestBusController(Controller):
    """
    This controller is only useful for test purpose. Bus is unavailable in test mode, but there is no way to know,
    at client side, if we are running in test mode or not. This route can be called while running tours to mock
    some behaviour in function of the test mode status (activated or not).

    E.g. : To test the livechat and to check there is no duplicates in message displayed in the chatter,
    in test mode, we need to mock a 'message added' notification that is normally triggered by the bus.
    In Normal mode, the bus triggers itself the notification.
    """
    @route('/bus/test_mode_activated', type="json", auth="public")
    def is_test_mode_activated(self):
        return request.registry.in_test_mode()
