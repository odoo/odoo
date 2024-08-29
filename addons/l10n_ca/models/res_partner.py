from odoo import fields, models
from odoo.addons import base


class ResPartner(models.Model, base.ResPartner):

    l10n_ca_pst = fields.Char(string='PST number', help='Canadian Provincial Tax Identification Number')
