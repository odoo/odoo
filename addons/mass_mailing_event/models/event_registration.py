# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventRegistration(models.Model):
    _inherit = 'event.registration'
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        return [('state', 'not in', ['cancel', 'draft'])]
