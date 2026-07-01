from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import pandas

class IrCron(models.Model):
    _name = 'ir.cron'
    _inherit = 'ir.cron'

    table_ids = fields.One2many('izi.table', 'cron_id', string='Tables')
    analytic = fields.Boolean('For Analytic Purpose')

class ServerAction(models.Model):
    _inherit = 'ir.actions.server'

    def _get_eval_context(self, action=None):
        eval_context = super(ServerAction, self)._get_eval_context(action=action)
        if self.usage == 'ir_cron':
            cron = self.env['ir.cron'].search(['|', ('active', '=', True), ('active', '=', False), ('ir_actions_server_id', '=', self.id)], limit=1)
            eval_context['cron'] = cron
            if cron.table_ids:
                eval_context['izi_table'] = cron.table_ids[0]
        eval_context['self'] = self
        eval_context['izi'] = self.env['izi.tools']
        return eval_context
    
    def run_by_name(self, action_name):
        action = self.env['ir.actions.server'].search([('name', '=', action_name)], limit=1)
        if action:
            return action.run()
        else:
            raise UserError('Action Not Found')
    
    def _run_action_code_multi(self, eval_context):
        res = super(ServerAction, self)._run_action_code_multi(eval_context)
        if eval_context.get('response'):
            return eval_context.get('response')
        # response = {
        #   'dataframe':,
        #   'data':,
        # }
        if 'res_dataframe' in eval_context and isinstance(eval_context.get('res_dataframe'), pandas.DataFrame):
            return {
                'dataframe': eval_context.get('res_dataframe'),
            }
        if 'res_data' in eval_context and isinstance(eval_context.get('res_data'), list):
            if eval_context.get('res_data'):
                first_record = eval_context.get('res_data')[0]
                if isinstance(first_record, dict):
                    try:
                        dataframe = pandas.DataFrame(eval_context.get('res_data'))
                        return {
                            'dataframe': dataframe,
                        }
                    except:
                        return res
        return res