from openerp import models, api

class account_unreconcile(models.TransientModel):
    _name = "account.unreconcile"
    _description = "Account Unreconcile"

    @api.multi
    def trans_unrec(self):
        if self._context.get('active_ids', False):
            self.env['account.move.line']._remove_move_reconcile(self._context['active_ids'])
        return {'type': 'ir.actions.act_window_close'}


class account_unreconcile_reconcile(models.TransientModel):
    _name = "account.unreconcile.reconcile"
    _description = "Account Unreconcile Reconcile"

    @api.multi
    def trans_unrec_reconcile(self):
        if self._context.get('active_ids', False):
            self.env['account.move.reconcile'].unlink(self._context.get('active_ids'))
        return {'type': 'ir.actions.act_window_close'}
