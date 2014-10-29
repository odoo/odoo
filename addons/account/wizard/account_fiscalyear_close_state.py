# -*- coding: utf-8 -*-
from openerp import models, fields, api


class account_fiscalyear_close_state(models.TransientModel):
    """
    Closes  Account Fiscalyear
    """
    _name = "account.fiscalyear.close.state"
    _description = "Fiscalyear Close state"

    fy_id = fields.Many2one('account.fiscalyear', \
        string='Fiscal Year to Close', required=True, help="Select a fiscal year to close")

    @api.multi
    def data_save(self):
        """
        This function close account fiscalyear
        """

        for data in  self.read():
            fy_id = data['fy_id'][0]

#             cr.execute('UPDATE account_journal_period ' \
#                         'SET state = %s ' \
#                         'WHERE period_id IN (SELECT id FROM account_period \
#                         WHERE fiscalyear_id = %s)',
#                     ('done', fy_id))
            self._cr.execute('UPDATE account_period SET state = %s ' \
                    'WHERE fiscalyear_id = %s', ('done', fy_id))
            self._cr.execute('UPDATE account_fiscalyear ' \
                    'SET state = %s WHERE id = %s', ('done', fy_id))
            self.invalidate_cache()

            return {'type': 'ir.actions.act_window_close'}
