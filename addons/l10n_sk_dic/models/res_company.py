# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # l10n_sk defines income_tax_id as a stored field on res.company only, which
    # cannot be used for partners. Point it at the partner field instead, so the
    # value lives in a single place. It is kept stored to leave the existing column in place.
    income_tax_id = fields.Char(related='partner_id.l10n_sk_dic', string="DIČ", store=True, readonly=False)
