from openerp import models, api

class account_move_line_select(models.TransientModel):
    """
        Account move line select
    """
    _name = "account.move.line.select"
    _description = "Account move line select"

    @api.multi
    def open_window(self):
        fiscalyear_obj = self.env['account.fiscalyear']

        context = dict(self._context or {})
        if not context.get('fiscalyear'):
            fiscalyears = fiscalyear_obj.search([('state', '=', 'draft')])
        else:
            fiscalyears = fiscalyear_obj.browse([context.get('fiscalyear')])

        period_ids = []
        if fiscalyears:
            for fiscalyear in fiscalyears:
                for period in fiscalyear.period_ids:
                    period_ids.append(period.id)
            domain = str(('period_id', 'in', period_ids))

        result = self.env.ref('account', 'action_move_line_tree1')
        result = result.read()[0]
        result['context'] = {
            'fiscalyear': False,
            'account_id': context['active_id'],
            'active_id': context['active_id'],
        }

        if context['active_id']:
            acc_data = self.env['account.account'].browse(context['active_id']).child_consol_ids
            if acc_data:
                result['context'].update({'consolidate_children': True})
        result['domain']=result['domain'][0:-1]+','+domain+result['domain'][-1]
        return result

