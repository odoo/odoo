from openerp import models, api, _
from openerp.exceptions import Warning

class account_state_open(models.TransientModel):
    _name = 'account.state.open'
    _description = 'Account State Open'

    @api.multi
    def change_inv_state(self):
        active_ids = self._context.get('active_ids')
        if isinstance(active_ids, list):
            invoice = self.env['account.invoice'].browse(active_ids[0])
            if invoice.reconciled:
                raise Warning(_('Invoice is already reconciled.'))
            invoice.signal_workflow('open_test')
        return {'type': 'ir.actions.act_window_close'}
