# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import event


class EventRegistration(event.EventRegistration):
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        return [('state', 'not in', ['cancel', 'draft'])]
