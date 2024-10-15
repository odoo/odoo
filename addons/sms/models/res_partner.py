# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import phone_validation, mail


class ResPartner(phone_validation.MailThreadPhone, mail.ResPartner, phone_validation.ResPartner):
