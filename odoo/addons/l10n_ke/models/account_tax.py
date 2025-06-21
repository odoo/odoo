# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ke_item_code_id = fields.Many2one(
        'l10n_ke.item.code',
        string='KRA Item Code',
        help='KRA code that describes a tax rate or exemption on specific products or services.',
    )

    @api.onchange('amount')
    def _onchange_l10n_ke_item_code_id(self):
        """ When the amount of the tax changes this field is reset """
        for tax in self:
            if tax._origin.amount != tax.amount:
                tax.l10n_ke_item_code_id = None
