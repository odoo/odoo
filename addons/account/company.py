# -*- coding: utf-8 -*-

from openerp import models, fields

class res_company(models.Model):
    _inherit = "res.company"

    expects_chart_of_accounts = fields.Boolean(string='Expects a Chart of Accounts', default=True)
    tax_calculation_rounding_method = fields.Selection([
            ('round_per_line', 'Round per Line'),
            ('round_globally', 'Round Globally'),
        ], default='round_per_line', string='Tax Calculation Rounding Method',
        help="If you select 'Round per Line' : for each tax, the tax amount will first be computed and rounded for each PO/SO/invoice line and then these rounded amounts will be summed, leading to the total amount for that tax. If you select 'Round Globally': for each tax, the tax amount will be computed for each PO/SO/invoice line, then these amounts will be summed and eventually this total tax amount will be rounded. If you sell with tax included, you should choose 'Round per line' because you certainly want the sum of your tax-included line subtotals to be equal to the total amount with taxes.")
    paypal_account = fields.Char(string='Paypal Account', size=128, help="Paypal username (usually email) for receiving online payments.")
    overdue_msg = fields.Text(string='Overdue Payments Message', translate=True,
        default='''Dear Sir/Madam,

Our records indicate that some payments on your account are still due. Please find details below.
If the amount has already been paid, please disregard this notice. Otherwise, please forward us the total amount stated below.
If you have any queries regarding your account, Please contact us.

Thank you in advance for your cooperation.
Best Regards,''')
