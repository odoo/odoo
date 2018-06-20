# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class Partner(models.Model):
    """ Update partner to add blacklist fields that can be used
       to restrict usage of automatic email templates. """
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.mass_mailing.blacklist.mixin']

    # Override method from the blacklist mixin
    def _blacklist_get_email_field_name(self):
        return ['email']
