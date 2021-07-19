# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp

class SriPayment(models.Model):

    _name="l10n.ec.sri.payment"

    name = fields.Char('Nombre')
    code = fields.Char('Código')