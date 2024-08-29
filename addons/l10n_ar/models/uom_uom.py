# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import uom
from odoo import fields, models


class UomUom(models.Model, uom.UomUom):


    l10n_ar_afip_code = fields.Char('Code', help='Argentina: This code will be used on electronic invoice.')
