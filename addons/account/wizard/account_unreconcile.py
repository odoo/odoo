from openerp import models, api

class account_unreconcile(models.TransientModel):
    _name = "account.unreconcile"
    _description = "Account Unreconcile"

    @api.multi
    def trans_unrec(self):
        context = dict(self._context or {})
        if context.get('active_ids', False):
            self.env['account.move.line'].browse(context.get('active_ids'))._remove_move_reconcile()
        return {'type': 'ir.actions.act_window_close'}


class account_unreconcile_reconcile(models.TransientModel):
    _name = "account.unreconcile.reconcile"
    _description = "Account Unreconcile Reconcile"

    @api.multi
    def trans_unrec_reconcile(self):
        context = dict(self._context or {})
        if context.get('active_ids', False):
            self.env['account.move.reconcile'].browse(context.get('active_ids')).unlink()
        return {'type': 'ir.actions.act_window_close'}
