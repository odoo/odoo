# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import web, portal, bus


class IrHttp(bus.IrHttp, web.IrHttp, portal.IrHttp):

    def session_info(self):
        """
        Override this method to enable the 'Insert in spreadsheet' button in the
        web client.
        """
        res = super().session_info()
        res["can_insert_in_spreadsheet"] = False
        return res
