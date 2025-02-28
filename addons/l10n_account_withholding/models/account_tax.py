# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):
    """
    Withholding taxes are unique in their computation; they should not affect the invoice MOST OF THE TIME.
    The only special case is that price-excluded withholding taxes will affect the SUBTOTAL of an invoice line.

    However, on a withholding line (payment register wizard/payment), we will compute the tax amounts as we
    need to register their value when the payment is itself registered.

    The following examples will highlight the expected amounts in different scenarios.
    We assume a quantity of 1 in each example for simplicity

    For the following scenarios:
    Tax A: Price-excluded withholding tax of 10%
    Tax B: Price-included withholding tax of 10%
    Tax C: Price-excluded tax of 15%, which affects the base of other taxes
    Tax D: Price-excluded tax of 15%, which does not affect the base of other taxes
    Tax E: Price-included tax of 15%, which affects the base of other taxes
    Tax F: Price-included tax of 15%, which does not affect the base of other taxes

    Scenarios 1 to 5 are about the withholding tax Price-excluded (A)
    Scenarios 6 to 10 are about the withholding tax Price-included (B)

    Product Line is the product line on the invoice.
    Withholding Line is the line appearing in the payment register.

    Scenario 1:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                   900
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |        900 | A    |     1000 |  1000 |     |        1000 |        100 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
    The withholding tax being price-excluded, the subtotal is adapted to include the tax.
    This is so that the tax does not affect the invoice at the time of registering.
    When registering the withholding tax, we calculate the tax amount and reduce the payment from
    this amount.

    Scenario 2:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                  1035
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |        900 | C, A |     1000 |  1150 |     |        1150 |        115 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
    We recompute the subtotal as above, and then apply the price-excluded tax based on that subtotal.
    On the withholding line, we calculate the tax amount based on the TOTAL PRICE of the line.

    Scenario 3:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                   900
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |        900 | E, A |   869.57 |  1000 |     |        1000 |        100 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
    In this case, the subtotal will be computed to exclude the 15% tax E from the subtotal you would
    have with only the withholding tax (1000).
    The payment registration will be the same as for Scenario 1.

    Scenario 4:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                  1050
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |        900 | D, A |    1000  |  1150 |     |        1000 |        100 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
    Similar to Scenario 2, but in this case the withholding tax base is not affected by the regular
    tax.

    Scenario 5:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                913.04
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |        900 | F, A |  869.57  |  1000 |     |      869.57 |      86.96 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
    Similar to Scenario 3, but in this case the withholding tax base is not affected by the regular
    tax.

    Scenario 6:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                   900
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |       1000 | B    |     1000 |  1000 |     |        1000 |        100 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
    With price-included withholding tax (the default), there is no effect on the invoice.
    The main difference with price-excluded is that in these cases, the subtotal will match the price unit * quantity.
    The withholding line amounts are the same as for price-excluded taxes. (this will be the case for each scenario)
    This means that when calculating the withholding line amount for price-included withholding tax,
    the calculation should treat these as tax-excluded taxes.

    Scenario 7:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                  1035
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |       1000 | C, B |     1000 |  1150 |     |        1150 |        115 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯

    Scenario 8:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                   900
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |       1000 | E, B |   869.57 |  1000 |     |        1000 |        100 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯

    Scenario 9:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                  1050
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |       1000 | D, B |    1000  |  1150 |     |        1000 |        100 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯

    Scenario 10:
    ‾‾‾‾‾‾‾‾‾‾‾
    Product Line                                  Withholding Line                  Payment Total
    ______________________________________       __________________________                913.04
   | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
   |       1000 | F, B |  869.57  |  1000 |     |      869.57 |      86.96 |
    ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯

    Note that these cases do not include multiple withholding taxes; the same logic would apply.
    Withholding taxes can affect each other, in which case it will be visible in the payment register.
    """
    _inherit = 'account.tax'

    # ------------------
    # Fields declaration
    # ------------------

    is_withholding_tax_on_payment = fields.Boolean(
        string="Withholding On Payment",
        help="If enabled, this tax will not affect journal entries until the registration of payment.",
    )
    withholding_sequence_id = fields.Many2one(
        string='Withholding Sequence',
        help='Label displayed on Journal Items and Payment Receipts.',
        comodel_name='ir.sequence',
        copy=False,
        check_company=True,
    )
    color = fields.Integer(compute='_compute_color')

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    def _compute_color(self):
        for tax in self:
            tax.color = 1 if tax.is_withholding_tax_on_payment else 0

    # ----------------------------
    # Onchange, Constraint methods
    # ----------------------------

    @api.onchange('is_withholding_tax_on_payment')
    def _onchange_is_withholding_tax_on_payment(self):
        """ Ensure that we don't keep cash basis enabled if it was before checking the withholding tax option. """
        if self.is_withholding_tax_on_payment:
            self.tax_exigibility = 'on_invoice'

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    # def _eval_tax_amount_price_excluded(self, batch, raw_base, evaluation_context):
    #     # EXTENDS 'account'
    #     self.ensure_one()
    #     if self.is_withholding_tax_on_payment and self.amount_type == 'percent':
    #         return 0
    #     return super()._eval_tax_amount_price_excluded(batch, raw_base, evaluation_context)

    def _eval_tax_amount_price_included(self, batch, raw_base, evaluation_context):
        # EXTENDS 'account'
        if self.is_withholding_tax_on_payment and self.amount_type == 'percent':
            return raw_base * self.amount / 100.0
        return super()._eval_tax_amount_price_included(batch, raw_base, evaluation_context)

    # @api.model
    # def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
    #     """
    #     When working with price-excluded withholding taxes, we want the subtotal to be affected.
    #     To do so, we adjust the price_unit before computing the tax details; which will achieve the
    #     adjustment of the subtotal and make sure it is used when computing subsequent taxes.
    #     """
    #     price_unit = base_line['price_unit']
    #     for withholding_tax in base_line['tax_ids'].filtered('is_withholding_tax_on_payment'):
    #         if not withholding_tax.price_include:
    #             amount = (price_unit / (1 - (withholding_tax.amount / 100))) - price_unit
    #             base_line['price_unit'] += amount
    #     return super()._add_tax_details_in_base_line(base_line, company, rounding_method)
    #
    # @api.model
    # def prepare_tax_extra_data(self, tax, special_mode, **kwargs):
    #     """
    #     For the purpose of tax computation (when the context key is set) every withholding tax will be considered
    #     price-excluded.
    #     """
    #     # todo not forget to adapt js for all of this
    #     res = super().prepare_tax_extra_data(tax, special_mode, **kwargs)
    #     if tax.is_withholding_tax_on_payment and self.env.context.get('include_withholding_taxes'):
    #         res['price_include'] = False
    #     return res
    #
    # def _get_tax_details(
    #     self,
    #     price_unit,
    #     quantity,
    #     precision_rounding=0.01,
    #     rounding_method='round_per_line',
    #     product=None,
    #     special_mode=False,
    #     manual_tax_amounts=None,
    # ):
    #     """
    #     Withholding taxes could have some effects when taxes are computed, and thus we do use them in _get_tax_details.
    #     But unless explicitly asked for, we do not want to return any of their information, and we will remove them from the res.
    #     """
    #     res = super()._get_tax_details(price_unit, quantity, precision_rounding, rounding_method, product, special_mode, manual_tax_amounts)
    #
    #     if not self.env.context.get('include_withholding_taxes'):
    #         res['taxes_data'] = [tax_data for tax_data in res['taxes_data'] if not tax_data['tax'].is_withholding_tax_on_payment]
    #
    #     return res
