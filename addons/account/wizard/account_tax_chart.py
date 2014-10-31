from openerp import models, fields, api, _

class account_tax_chart(models.TransientModel):
    """
    For Chart of taxes
    """
    _name = "account.tax.chart"
    _description = "Account tax chart"

    period_id = fields.Many2one('account.period', string='Period',
        default=lambda self: self._get_period())
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries'),],
        string='Target Moves', required=True, default='posted')

    @api.model
    def _get_period(self):
        """Return default period value"""
        period_ids = self.env['account.period'].find()
        return period_ids and period_ids[0] or False

    @api.multi
    def account_tax_chart_open_window(self):
        """
        Opens chart of Accounts
        @return: dictionary of Open account chart window on given fiscalyear and all Entries or posted entries
        """
        result = self.env.ref('account.action_tax_code_tree')
        result = result.read()[0]
        if self.period_id:
            result['context'] = str({'period_id': self.period_id.id, \
                                     'fiscalyear_id': self.period_id.fiscalyear_id.id, \
                                        'state': self.target_move})
            period_code = self.period_id.code
            result['name'] += period_code and (':' + period_code) or ''
        else:
            result['context'] = str({'state': self.target_move})

        return result

