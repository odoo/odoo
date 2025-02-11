from odoo import fields, models

L10N_IT_PAYMENT_METHOD_SELECTION = [
    ('MP01', "MP01 - Cash"),
    ('MP02', "MP02 - Check"),
    ('MP03', "MP03 - Cashier's check"),
    ('MP04', "MP04 - Cash at the Treasury"),
    ('MP05', "MP05 - Wire transfer"),
    ('MP06', "MP06 - Promissory note"),
    ('MP07', "MP07 - Bank slip"),
    ('MP08', "MP08 - Payment card"),
    ('MP09', "MP09 - RID"),
    ('MP10', "MP10 - RID users"),
    ('MP11', "MP11 - Fast RID"),
    ('MP12', "MP12 - RIBA"),
    ('MP13', "MP13 - MAV"),
    ('MP14', "MP14 - Treasury receipt"),
    ('MP15', "MP15 - Transfer of special accounting accounts"),
    ('MP16', "MP16 - Bank direct debit"),
    ('MP17', "MP17 - Postal domiciliation"),
    ('MP18', "MP18 - Postal account slip"),
    ('MP19', "MP19 - SEPA Direct Debit"),
    ('MP20', "MP20 - SEPA Direct Debit CORE"),
    ('MP21', "MP21 - SEPA Direct Debit B2B"),
    ('MP22', "MP22 - Withholding from sums already collected"),
    ('MP23', "MP23 - PagoPA"),
]


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    l10n_it_payment_method = fields.Selection(
        selection=L10N_IT_PAYMENT_METHOD_SELECTION,
        string="Italian Payment Method",
        default='MP05',
    )
