from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class Home(Home):

    @http.route()
    @add_guest_to_context
    def web_login(self, redirect=None, **kw):
        guest = request.env["mail.guest"]._get_guest_from_context()
        channel_ids = guest.sudo().channel_ids
        res = super().web_login(redirect)
        if request.httprequest.method == 'POST':
            print("==================")
            print(channel_ids.ids, guest.id)
            print("==================")
            channel_members = request.env["discuss.channel.member"].sudo().search([
                ["channel_id", "in", channel_ids.ids],
                ["guest_id", "=", guest.id]
            ])
            print(channel_members)
            for member in channel_members:
                print(member)
                member.sudo().write({
                    "guest_id": None,
                    "partner_id": request.env.user.partner_id
                })
        return res
