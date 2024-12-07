# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventRegistration(models.Model):
    _inherit = 'event.registration'
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        default_domain = [('state', 'not in', ['cancel', 'draft'])]
        default_mailing_model_id = self.env.context.get('default_mailing_model_id')
        if mailing.mailing_model_id.id == default_mailing_model_id:
            return self.env.context.get('default_mailing_domain', default_domain)
        return default_domain
