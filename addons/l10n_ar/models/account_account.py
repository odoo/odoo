# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountAccount(models.Model):

    _inherit = 'account.account'

    l10n_ar_vat_f2002_category_id = fields.Many2one(
        'l10n_ar.afip.vat.f2002.category',
        auto_join=True,
        string='Categoría IVA f2002',
    )
