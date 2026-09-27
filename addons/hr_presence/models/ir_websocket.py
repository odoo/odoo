# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.api import Environment
from odoo.fields import Datetime
from odoo.http import request
from odoo.modules.registry import Registry
from odoo.addons.bus.websocket import wsrequest


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _update_mail_presence(self, inactivity_period):
        super()._update_mail_presence(inactivity_period)
        #  This method can either be called due to an http or a
        #  websocket request. The request itself is necessary to
        #  retrieve the current guest. Let's retrieve the proper
        #  request.
        req = request or wsrequest
        if self.env.user._is_internal():
            ip_address = req.httprequest.remote_addr
            domain = [
                ("create_uid", "=", self.env.user.id),
                ("ip", "=", ip_address),
                ("create_date", ">=", fields.Date.today()),
            ]
            if not self.env["res.users.log"].sudo().search_count(domain, limit=1):
                with Registry(self.env.cr.dbname).cursor() as cr:
                    env = Environment(cr, self.env.user.id, {})
                    env["res.users.log"].sudo().create({"ip": ip_address})
