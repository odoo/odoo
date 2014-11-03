import time

from openerp import models, fields, api, _
from openerp.tools.float_utils import float_round
import openerp.addons.decimal_precision as dp

class account_move_line_reconcile(models.TransientModel):
    """
    Account move line reconcile wizard, it checks for the write off the reconcile entry or directly reconcile.
    """
    _name = 'account.move.line.reconcile'
    _description = 'Account move line reconcile'

    trans_nbr = fields.Integer(string='# of Transaction', readonly=True)
    credit = fields.Float(string='Credit amount', readonly=True, digits=dp.get_precision('Account'))
    debit = fields.Float(string='Debit amount', readonly=True, digits=dp.get_precision('Account'))
    writeoff = fields.Float(string='Write-Off amount', readonly=True, digits=dp.get_precision('Account'))

    @api.model
    def default_get(self, fields):
        res = super(account_move_line_reconcile, self).default_get(fields)
        data = self.trans_rec_get(self._context['active_ids'])
        if 'trans_nbr' in fields:
            res.update({'trans_nbr':data['trans_nbr']})
        if 'credit' in fields:
            res.update({'credit':data['credit']})
        if 'debit' in fields:
            res.update({'debit':data['debit']})
        if 'writeoff' in fields:
            res.update({'writeoff':data['writeoff']})
        return res

    @api.multi
    def trans_rec_get(self):
        credit = debit = 0
        account_id = False
        count = 0
        for line in self.env['account.move.line'].browse(self._context['active_ids']):
            if not line.reconcile_id and not line.reconcile_id.id:
                count += 1
                credit += line.credit
                debit += line.debit
                account_id = line.account_id.id
        precision = self.env['decimal.precision'].precision_get('Account')
        writeoff = float_round(debit-credit, precision_digits=precision)
        credit = float_round(credit, precision_digits=precision)
        debit = float_round(debit, precision_digits=precision)
        return {'trans_nbr': count, 'account_id': account_id, 'credit': credit, 'debit': debit, 'writeoff': writeoff}

    @api.multi
    def trans_rec_addendum_writeoff(self):
        return self.env['account.move.line.reconcile.writeoff'].trans_rec_addendum()

    @api.multi
    def trans_rec_reconcile_partial_reconcile(self):
        return self.env['account.move.line.reconcile.writeoff'].trans_rec_reconcile_partial()

    @api.multi
    def trans_rec_reconcile_full(self):
        date = False
        period_id = False
        journal_id= False
        account_id = False

        date = time.strftime('%Y-%m-%d')
        ids = self.env['account.period'].find(dt=date)
        if ids:
            period_id = ids[0]
        self.env['account.move.line'].reconcile(self._context['active_ids'], 'manual', account_id,
                                        period_id, journal_id)
        return {'type': 'ir.actions.act_window_close'}


class account_move_line_reconcile_writeoff(models.TransientModel):
    """
    It opens the write off wizard form, in that user can define the journal, account, analytic account for reconcile
    """
    _name = 'account.move.line.reconcile.writeoff'
    _description = 'Account move line reconcile (writeoff)'

    journal_id = fields.Many2one('account.journal', string='Write-Off Journal', required=True)
    writeoff_acc_id = fields.Many2one('account.account', string='Write-Off account', required=True, domain=[('deprecated', '=', False)])
    date_p = fields.Date(string='Date', default=lambda self:time.strftime('%Y-%m-%d'))
    comment = fields.Char(string='Comment', required=True, default='Write-off')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', domain=[('parent_id', '!=', False)])


    @api.multi
    def trans_rec_addendum(self):
        model_data_ids = self.env['ir.model.data'].search([('model', '=', 'ir.ui.view'), ('name', '=', 'account_move_line_reconcile_writeoff')])
        resource_id = model_data_ids.read(fields=['res_id'])[0]['res_id']
        return {
            'name': _('Reconcile Writeoff'),
            'context': self._context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.line.reconcile.writeoff',
            'views': [(resource_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def trans_rec_reconcile_partial(self):
        context = dict(self._context or {})
        self.env['account.move.line'].reconcile_partial(context.get('active_ids', []) , 'manual')
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def trans_rec_reconcile(self):
        context = self._context.copy()
        data = self.read()[0]
        account_id = data['writeoff_acc_id'][0]
        context['date_p'] = data['date_p']
        journal_id = data['journal_id'][0]
        context['comment'] = data['comment']
        if data['analytic_id']:
            context['analytic_id'] = data['analytic_id'][0]
        if context['date_p']:
            date = context['date_p']
        ids = self.env['account.period'].with_context(context).find(dt=date)
        if ids:
            period_id = ids[0]

        self.env['account.move.line'].with_context(context).reconcile(self._context['active_ids'], 'manual', account_id,
                period_id, journal_id)
        return {'type': 'ir.actions.act_window_close'}

