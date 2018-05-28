from odoo import models, fields, api, _
from odoo.tools.float_utils import float_round


class AccountMoveLineReconcile(models.TransientModel):
    """
    Account move line reconcile wizard, it checks for the write off the reconcile entry or directly reconcile.
    """
    _name = 'account.move.line.reconcile'
    _description = 'Account move line reconcile'

    trans_nbr = fields.Integer(string='Transaction Count', readonly=True)
    credit = fields.Float(string='Credit amount', readonly=True, digits=0)
    debit = fields.Float(string='Debit amount', readonly=True, digits=0)
    writeoff = fields.Float(string='Write-Off amount', readonly=True, digits=0)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveLineReconcile, self).default_get(fields)
        data = self.trans_rec_get()
        if 'trans_nbr' in fields:
            res.update({'trans_nbr': data['trans_nbr']})
        if 'credit' in fields:
            res.update({'credit': data['credit']})
        if 'debit' in fields:
            res.update({'debit': data['debit']})
        if 'writeoff' in fields:
            res.update({'writeoff': data['writeoff']})
        return res

    @api.multi
    def trans_rec_get(self):
        context = self._context or {}
        credit = debit = 0
        lines = self.env['account.move.line'].browse(context.get('active_ids', []))
        for line in lines:
            if not line.full_reconcile_id:
                credit += line.credit
                debit += line.debit
        precision = self.env.user.company_id.currency_id.decimal_places
        writeoff = float_round(debit - credit, precision_digits=precision)
        credit = float_round(credit, precision_digits=precision)
        debit = float_round(debit, precision_digits=precision)
        return {'trans_nbr': len(lines), 'credit': credit, 'debit': debit, 'writeoff': writeoff}

    @api.multi
    def trans_rec_addendum_writeoff(self):
        return self.env['account.move.line.reconcile.writeoff'].trans_rec_addendum()

    @api.multi
    def trans_rec_reconcile_partial_reconcile(self):
        return self.env['account.move.line.reconcile.writeoff'].trans_rec_reconcile_partial()

    @api.multi
    def trans_rec_reconcile_full(self):
        move_lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
        #Don't consider entries that are already reconciled
        move_lines_filtered = move_lines.filtered(lambda aml: not aml.reconciled)
        move_lines_filtered.reconcile()
        return {'type': 'ir.actions.act_window_close'}


class AccountMoveLineReconcileWriteoff(models.TransientModel):
    """
    It opens the write off wizard form, in that user can define the journal, account, analytic account for reconcile
    """
    _name = 'account.move.line.reconcile.writeoff'
    _description = 'Account move line reconcile (writeoff)'

    journal_id = fields.Many2one('account.journal', string='Write-Off Journal', required=True)
    writeoff_acc_id = fields.Many2one('account.account', string='Write-Off account', required=True, domain=[('deprecated', '=', False)])
    date_p = fields.Date(string='Date', default=fields.Date.context_today)
    comment = fields.Char(required=True, default='Write-off')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    @api.multi
    def trans_rec_addendum(self):
        view = self.env.ref('account.account_move_line_reconcile_writeoff')
        return {
            'name': _('Reconcile Writeoff'),
            'context': self._context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.line.reconcile.writeoff',
            'views': [(view.id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def trans_rec_reconcile_partial(self):
        context = self._context or {}
        self.env['account.move.line'].browse(context.get('active_ids', [])).reconcile()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def trans_rec_reconcile(self):
        context = dict(self._context or {})
        context['date_p'] = self.date_p
        context['comment'] = self.comment
        if self.analytic_id:
            context['analytic_id'] = self.analytic_id.id
        move_lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
        #Don't consider entries that are already reconciled
        move_lines_filtered = move_lines.filtered(lambda aml: not aml.reconciled)
        writeoff = move_lines_filtered.with_context(context).reconcile(self.writeoff_acc_id, self.journal_id)
        return {'type': 'ir.actions.act_window_close'}
