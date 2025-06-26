# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_tax_type = fields.Selection(
        selection=[
            ('01', "Sales Tax"),
            ('02', "Service Tax"),
            ('03', "Tourism Tax"),
            ('04', "High-Value Goods Tax"),
            ('05', "Sales Tax on Low Value Goods"),
            ('06', "Not Applicable"),
            ('E', "Tax exemption (where applicable)"),
        ],
        string="Malaysian Tax Type",
        compute="_compute_l10n_my_tax_type",
        store=True,
        readonly=False,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('amount', 'country_id', 'tax_scope')
    def _compute_l10n_my_tax_type(self):
        """ Compute default tax type based on a few factors. """
        for tax in self:
            if tax.country_id.code != 'MY':
                tax.l10n_my_tax_type = False
            else:
                if tax.amount == 0:
                    tax.l10n_my_tax_type = 'E'
                elif tax.tax_scope == 'consu':
                    tax.l10n_my_tax_type = '01'
                elif tax.tax_scope == 'service':
                    tax.l10n_my_tax_type = '02'
                else:
                    tax.l10n_my_tax_type = '06'
