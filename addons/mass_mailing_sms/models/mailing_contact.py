# -*- coding: utf-8 -*-
from odoo.addons import phone_validation, mass_mailing
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingContact(models.Model, mass_mailing.MailingContact, phone_validation.MailThreadPhone):

    mobile = fields.Char(string='Mobile')
