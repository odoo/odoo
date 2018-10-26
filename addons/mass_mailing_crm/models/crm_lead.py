# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Lead(models.Model):
    _name = "crm.lead"
    _inherit = ['crm.lead']

    @api.multi
    def message_get_default_recipients(self):
        return {
            r.id : {'partner_ids': [],
                    'email_to': r.email_normalized,
                    'email_cc': False}
            for r in self.sudo()
        }
