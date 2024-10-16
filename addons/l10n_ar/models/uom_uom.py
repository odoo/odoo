# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import account


class UomUom(account.UomUom):


    l10n_ar_afip_code = fields.Char('Code', help='Argentina: This code will be used on electronic invoice.')
