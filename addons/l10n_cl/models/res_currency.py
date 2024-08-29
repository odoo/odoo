# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base
from odoo import _, api, fields, models


class ResCurrency(models.Model, base.ResCurrency):

    l10n_cl_currency_code = fields.Char('Currency Code', translate=True)
    l10n_cl_short_name = fields.Char('Short Name', translate=True)
