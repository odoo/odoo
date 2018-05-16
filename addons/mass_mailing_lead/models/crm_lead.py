# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class MassMailingLead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'mail.mass_mailing.blacklist.mixin']

    # Override _email_field_name from the blacklist mixin
    _email_field_name = ['email_from']
