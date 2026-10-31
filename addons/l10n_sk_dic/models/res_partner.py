# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_sk_dic = fields.Char(string="DIČ", help="Tax identification number assigned to every Slovak taxpayer upon registration, whether or not they are registered for VAT")

    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_sk_dic']
