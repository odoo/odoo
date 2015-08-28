# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Lead(models.Model):
    _inherit = 'crm.lead'

    def website_form_input_filter(self, request, values):
        values.setdefault('medium_id', self.env.ref('utm.utm_medium_email').id)
        return values
