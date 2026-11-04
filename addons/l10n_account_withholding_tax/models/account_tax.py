# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # ------------------
    # Fields declaration
    # ------------------

    is_withholding_tax_on_payment = fields.Boolean(
        string="Withhold On Payment",
        help="If enabled, this tax will not affect your accounts until the registration of payments.",
    )
    withholding_sequence_id = fields.Many2one(
        string='Withholding Sequence',
        help='This sequence will be used to generate default numbers on payment withholding lines.',
        comodel_name='ir.sequence',
        copy=False,
        check_company=True,
    )

    # ----------------------------
    # Onchange, Constraint methods
    # ----------------------------

    @api.onchange('is_withholding_tax_on_payment')
    def _onchange_is_withholding_tax_on_payment(self):
        """ Ensure that we don't keep cash basis enabled if it was before checking the withholding tax option. """
        if self.is_withholding_tax_on_payment:
            self.tax_exigibility = 'on_invoice'
            self.price_include_override = 'tax_excluded'

    @api.onchange('amount')
    def _onchange_amount(self):
        """ Reset the is_withholding_tax_on_payment field when the amount is set to positive; as the field will be hidden. """
        if self.amount >= 0:
            self.is_withholding_tax_on_payment = False

    @api.constrains('amount_type', 'is_withholding_tax_on_payment')
    def _check_amount_type(self):
        """ The computation of withholding taxes needs to be limited in computation types to ensure that it works as expected. """
        for tax in self:
            if tax.is_withholding_tax_on_payment and tax.amount_type in ['group', 'division']:
                raise UserError(tax.env._("Withholding On Payment taxes cannot use the 'Group of Taxes' or the 'Percentage Tax Included' computations."))

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """
        Withholding taxes should not affect the tax computation unless explicitly required (via a specific key in the base line).
        This requires to adapt the tax computation slightly to achieve this behavior.
        """
        # EXTENDS 'account'
        if not base_line.get('calculate_withholding_taxes'):
            base_line['filter_tax_function'] = lambda t: not t.is_withholding_tax_on_payment
        super()._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)
