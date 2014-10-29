from openerp import models, fields, api, _


class account_common_partner_report(models.TransientModel):
    _name = 'account.common.partner.report'
    _description = 'Account Common Partner Report'
    _inherit = "account.common.report"

    result_selection = fields.Selection([
        ('customer','Receivable Accounts'), 
        ('supplier','Payable Accounts'),
        ('customer_supplier','Receivable and Payable Accounts')],
        string ="Partner's", required=True, default='customer')

    @api.multi
    def pre_print_report(self, data):
        data['form'].update(self.read(self.ids, ['result_selection'])[0])
        return data

