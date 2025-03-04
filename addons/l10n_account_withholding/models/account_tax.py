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

    @api.onchange('is_withholding_tax_on_payment')
    def _onchange_is_withholding_tax_on_payment(self):
        """ For proper computations, withholding taxes should have their amount type set to division.. """
        if self.is_withholding_tax_on_payment:
            self.amount_type = 'division'

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        base_line = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        # We support adding a new key in the base line dict to determine if the withholding taxes need to
        # be computed completely or not.
        base_line['calculate_withholding_taxes'] = kwargs.get('calculate_withholding_taxes', False)
        return base_line

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        # EXTENDS 'account'
        if not base_line.get('calculate_withholding_taxes'):
            # Adapt the price unit to properly affect the subtotal when using price_exclude tax
            base_line['tax_ids'] = base_line['tax_ids'].filtered(lambda t: not t.is_withholding_tax_on_payment or not t.price_include)
            price_unit = base_line['price_unit']
            for withholding_tax in base_line['tax_ids'].filtered('is_withholding_tax_on_payment'):
                base_line['price_unit'] += (price_unit / (1 - (withholding_tax.amount / 100))) - price_unit

        super()._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)

        if not base_line.get('calculate_withholding_taxes'):
            # Affect the tax total for price_exclude taxes to not add the tax on top of it.
            taxes_data = base_line['tax_details']['taxes_data']
            for tax_data in taxes_data:
                if tax_data['tax'].is_withholding_tax_on_payment:
                    base_line['tax_details']['taxes_data'].remove(tax_data)
                    raw_amount = tax_data['raw_tax_amount']
                    raw_amount_currency = tax_data['raw_tax_amount_currency']

                    base_line['tax_details']['raw_total_included'] -= raw_amount
                    base_line['tax_details']['raw_total_included_currency'] -= raw_amount_currency
