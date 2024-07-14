# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WhatsAppTemplateVariable(models.Model):
    _inherit = 'whatsapp.template.variable'

    def _portal_available_for_model(self):
        """
        list is defined here else we need to create bridge module
        :param model: model name
        :return: list of model name that have portal
        """
        available_for_model = super()._portal_available_for_model()
        return available_for_model + [
            'event.registration', # get_portal_url is owrride in event.registration
        ]
