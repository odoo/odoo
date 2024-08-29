# -*- coding: utf-8 -*-
from odoo.addons import phone_validation, base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model, phone_validation.MailThreadPhone, base.ResPartner):
