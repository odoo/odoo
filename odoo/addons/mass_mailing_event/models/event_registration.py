# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import models


class EventRegistration(models.Model):
    _inherit = 'event.registration'
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        default_mailing_model_id = self.env.context.get('default_mailing_model_id')
        default_mailing_domain = self.env.context.get('default_mailing_domain')
        if default_mailing_model_id and mailing.mailing_model_id.id == default_mailing_model_id and default_mailing_domain:
            return ast.literal_eval(default_mailing_domain)
        return [('state', 'not in', ['cancel', 'draft'])]
