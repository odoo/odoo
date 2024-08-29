# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base
from odoo import fields, models


class ResCurrency(models.Model, base.ResCurrency):


    l10n_ar_afip_code = fields.Char('AFIP Code', size=4, help='This code will be used on electronic invoice')
