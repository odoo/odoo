from odoo import fields, models
from odoo.addons import account


class ResPartner(account.ResPartner):

    l10n_ca_pst = fields.Char(string='PST number', help='Canadian Provincial Tax Identification Number')
