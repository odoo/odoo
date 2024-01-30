# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class WebClient(WebclientController):
<<<<<<< HEAD
    """Override to add CORS support."""

    @route("/im_livechat/cors/action", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_action(self, guest_token, **kwargs):
||||||| parent of f3db9f113786 (temp)
    @route("/im_livechat/cors/init_messaging", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_init_messaging(self, guest_token):
=======
    @route("/im_livechat/cors/init_messaging", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_init_messaging(self, guest_token, context=None):
>>>>>>> f3db9f113786 (temp)
        force_guest_env(guest_token)
<<<<<<< HEAD
        return self.mail_action(**kwargs)

    @route("/im_livechat/cors/data", methods=["POST"], type="json", auth="public", cors="*", readonly=True)
    def livechat_data(self, guest_token, **kwargs):
        force_guest_env(guest_token)
        return self.mail_data(**kwargs)
||||||| parent of f3db9f113786 (temp)
        return self.mail_init_messaging()
=======
        return self.mail_init_messaging(context=context)
>>>>>>> f3db9f113786 (temp)
