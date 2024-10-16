# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import phone_validation, mass_mailing


class MailingContact(mass_mailing.MailingContact, phone_validation.MailThreadPhone):

    mobile = fields.Char(string='Mobile')
