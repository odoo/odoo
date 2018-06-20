# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class MassMailingLead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'mail.mass_mailing.blacklist.mixin']

    # Override method from the blacklist mixin
    def _blacklist_get_email_field_name(self):
        return ['email_from']
