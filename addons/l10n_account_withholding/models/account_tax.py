# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_account_withholding_type = fields.Selection(
        string='Withholding Type',
        help='Defines how this tax is used when registering withholding taxes.',
        selection=[('supplier', 'Supplier'), ('customer', 'Customer')],
        compute="_compute_l10n_account_withholding_type",
        store=True,
        readonly=False,
    )
    l10n_account_withholding_sequence_id = fields.Many2one(
        string='Withholding Sequence',
        help='If no sequence provided then it will be required for you to enter a withholding number when registering one.',
        comodel_name='ir.sequence',
        copy=False,
        check_company=True,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('type_tax_use', 'country_code')
    def _compute_l10n_account_withholding_type(self):
        """ Ensure that a tax with any type tax use won't be set as withholding tax.
        These are expected to have a type tax use set to None.
        """
        for tax in self:
            withholding_type = tax.l10n_account_withholding_type
            if tax.type_tax_use != 'none':
                withholding_type = False
            tax.l10n_account_withholding_type = withholding_type
