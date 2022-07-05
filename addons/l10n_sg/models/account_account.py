from odoo import api, models

class AccountAccount(models.Model):
    _inherit = "account.account"

    @api.onchange('user_type_id')
    def _onchange_user_type_id(self):
        income_revenue = self.env.ref("account.data_account_type_revenue")
        other_income_revenue = self.env.ref("account.data_account_type_other_income")
        message = ""
        if self.user_type_id == income_revenue:
            message = "Please note that this account will be reflected in the Box 13: Revenus of the GST Return"
        elif self.user_type_id == other_income_revenue:
            message = "Please note that this account will not be reflected in the Box 13: Revenues of the GST Return"

        if self.user_type_id in income_revenue | other_income_revenue:
            return {
                'warning': {
                    'title': "Warning",
                    'message': message
                }
            }
