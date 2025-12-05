# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.webclient import WebclientController


class HrWebclientController(WebclientController):
    @classmethod
    def _get_supported_avatar_card_models(self):
        return [*super()._get_supported_avatar_card_models(), "resource.resource"]
