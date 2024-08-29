# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base_address_extended
from odoo import fields, models


class ResCity(models.Model, base_address_extended.ResCity):

    l10n_pe_code = fields.Char('Code', help='This code will help with the '
                               'identification of each city in Peru.')
