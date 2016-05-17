# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import odoo.workflow


class Workflow(models.Model):
    _name = "workflow"
    _table = "wkf"
    _order = "name"

    name = fields.Char('Name', required=True)
    osv = fields.Char('Resource Object', required=True, index=True)
    on_create = fields.Boolean('On Create', default=True, index=True)
    activities = fields.One2many('workflow.activity', 'wkf_id', string='Activities')

    @api.multi
    def copy(self, values):
        raise UserError(_("Duplicating workflows is not possible, please create a new workflow"))

    @api.multi
    def write(self, vals):
        odoo.workflow.clear_cache(self._cr, self._uid)
        return super(Workflow, self).write(vals)

    @api.model
    def get_active_workitems(self, res_model, res_id):
        cr = self._cr
        cr.execute("SELECT * FROM wkf WHERE osv=%s LIMIT 1", (res_model,))
        wkfinfo = cr.dictfetchone()
        workitems = []
        if wkfinfo:
            query = """ SELECT id FROM wkf_instance
                        WHERE res_id=%s AND wkf_id=%s
                        ORDER BY state LIMIT 1 """
            cr.execute(query, (res_id, wkfinfo['id']))
            inst_id = cr.fetchone()

            query = """ SELECT act_id, COUNT(*) FROM wkf_workitem
                        WHERE inst_id=%s GROUP BY act_id """
            cr.execute(query, (inst_id,))
            workitems = dict(cr.fetchall())
        return {'wkf': wkfinfo, 'workitems': workitems}

    @api.model
    def create(self, vals):
        odoo.workflow.clear_cache(self._cr, self._uid)
        return super(Workflow, self).create(vals)


class WorkflowActivity(models.Model):
    _name = "workflow.activity"
    _table = "wkf_activity"
    _order = "name"

    name = fields.Char('Name', required=True)
    wkf_id = fields.Many2one('workflow', string='Workflow', ondelete='cascade',
                             required=True, index=True)
    split_mode = fields.Selection([('XOR', 'Xor'), ('OR','Or'), ('AND','And')],
                                  string='Split Mode', size=3, required=True, default='XOR')
    join_mode = fields.Selection([('XOR', 'Xor'), ('AND', 'And')],
                                 string='Join Mode', size=3, required=True, default='XOR')
    kind = fields.Selection([('dummy', 'Dummy'), ('function', 'Function'),
                             ('subflow', 'Subflow'), ('stopall', 'Stop All')],
                            string='Kind', required=True, default='dummy')
    action = fields.Text('Python Action')
    action_id = fields.Many2one('ir.actions.server', string='Server Action', ondelete='set null')
    flow_start = fields.Boolean('Flow Start')
    flow_stop = fields.Boolean('Flow Stop')
    subflow_id = fields.Many2one('workflow', string='Subflow')
    signal_send = fields.Char('Signal (subflow.*)')
    out_transitions = fields.One2many('workflow.transition', 'act_from', string='Outgoing Transitions')
    in_transitions = fields.One2many('workflow.transition', 'act_to', string='Incoming Transitions')

    @api.multi
    def unlink(self):
        if not self._context.get('_force_unlink') and \
                self.env['workflow.workitem'].search([('act_id', 'in', self.ids)]):
            raise UserError(_('Please make sure no workitems refer to an activity before deleting it!'))
        super(WorkflowActivity, self).unlink()


class WorkflowTransition(models.Model):
    _name = "workflow.transition"
    _table = "wkf_transition"
    _rec_name = 'signal'
    _order = 'sequence,id'

    trigger_model = fields.Char('Trigger Object')
    trigger_expr_id = fields.Char('Trigger Expression')
    sequence = fields.Integer('Sequence', default=10)
    signal = fields.Char('Signal (Button Name)',
                         help="When the operation of transition comes from a button pressed in the client form, "
                              "signal tests the name of the pressed button. If signal is NULL, no button is necessary to validate this transition.")
    group_id = fields.Many2one('res.groups', string='Group Required',
                               help="The group that a user must have to be authorized to validate this transition.")
    condition = fields.Char('Condition', required=True, default='True',
                            help="Expression to be satisfied if we want the transition done.")
    act_from = fields.Many2one('workflow.activity', string='Source Activity',
                               ondelete='cascade', required=True, index=True,
                               help="Source activity. When this activity is over, the condition is tested to determine if we can start the ACT_TO activity.")
    act_to = fields.Many2one('workflow.activity', string='Destination Activity',
                             ondelete='cascade', required=True, index=True,
                             help="The destination activity.")
    wkf_id = fields.Many2one('workflow', related='act_from.wkf_id', string='Workflow')

    @api.multi
    def name_get(self):
        return [
            (line.id, line.signal or "%s+%s" % (line.act_from.name, line.act_to.name))
            for line in self
        ]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if name:
            domain = ['|', ('act_from', operator, name), ('act_to', operator, name)] + (args or [])
            return self.search(domain, limit=limit).name_get()
        return super(WorkflowTransition, self).name_search(name, args, operator, limit=limit)


class WorkflowInstance(models.Model):
    _name = "workflow.instance"
    _table = "wkf_instance"
    _rec_name = 'res_type'
    _log_access = False

    uid = fields.Integer('User')        # FIXME no constraint??
    wkf_id = fields.Many2one('workflow', string='Workflow', ondelete='cascade', index=True)
    res_id = fields.Integer('Resource ID')
    res_type = fields.Char('Resource Object')
    state = fields.Char('Status')
    transition_ids = fields.Many2many('workflow.transition', 'wkf_witm_trans', 'inst_id', 'trans_id')

    @api.model_cr_context
    def _auto_init(self):
        res = super(WorkflowInstance, self)._auto_init()
        cr = self._cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname=%s', ['wkf_instance_res_type_res_id_state_index'])
        if not cr.fetchone():
            cr.execute('CREATE INDEX wkf_instance_res_type_res_id_state_index ON wkf_instance (res_type, res_id, state)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname=%s', ['wkf_instance_res_id_wkf_id_index'])
        if not cr.fetchone():
            cr.execute('CREATE INDEX wkf_instance_res_id_wkf_id_index ON wkf_instance (res_id, wkf_id)')
        return res


class WorkflowWorkitem(models.Model):
    _name = "workflow.workitem"
    _table = "wkf_workitem"
    _rec_name = 'state'
    _log_access = False

    act_id = fields.Many2one('workflow.activity', string='Activity',
                             ondelete="cascade", required=True, index=True)
    wkf_id = fields.Many2one('workflow', related='act_id.wkf_id', string='Workflow')
    subflow_id = fields.Many2one('workflow.instance', string='Subflow',
                                 ondelete="set null", index=True)
    inst_id = fields.Many2one('workflow.instance', string='Instance',
                              ondelete="cascade", required=True, index=True)
    state = fields.Char('Status', index=True)


class WorkflowTriggers(models.Model):
    _name = "workflow.triggers"
    _table = "wkf_triggers"
    _log_access = False

    res_id = fields.Integer('Resource ID', size=128)
    model = fields.Char('Object')
    instance_id = fields.Many2one('workflow.instance', string='Destination Instance',
                                  ondelete="cascade")
    workitem_id = fields.Many2one('workflow.workitem', string='Workitem',
                                  ondelete="cascade", required=True)

    @api.model_cr_context
    def _auto_init(self):
        res = super(WorkflowTriggers, self)._auto_init()
        cr = self._cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname=%s', ['wkf_triggers_res_id_model_index'])
        if not cr.fetchone():
            cr.execute('CREATE INDEX wkf_triggers_res_id_model_index ON wkf_triggers (res_id, model)')
        return res
