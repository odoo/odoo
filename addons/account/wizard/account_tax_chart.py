from openerp import models, fields, api, _

class account_tax_chart(models.TransientModel):
    """
    For Chart of taxes
    """
    _name = "account.tax.chart"
    _description = "Account tax chart"

    date = fields.Date(string='Account Date',
        default=fields.Date.context_today)
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries'),],
        string='Target Moves', required=True, default='posted')

    @api.multi
    def account_tax_chart_open_window(self):
        """
        Opens chart of Accounts
        @return: dictionary of Open account chart window on given fiscalyear and all Entries or posted entries
        """
        result = self.env.ref('account.action_tax_code_tree')
        result = result.read()[0]
        if self.date:
            result['context'] = str({'date': self.date, \
                                      'state': self.target_move})
        else:
            result['context'] = str({'state': self.target_move})

        return result

