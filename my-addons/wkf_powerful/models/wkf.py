# -*- coding: utf-8 -*-
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from lxml import etree
from lxml.etree import XML, tostring
from .xml_templdate import *


class wkf_base(models.Model):
    _name = 'wkf.base'
    _description = 'Wkf Base'
    _def_wkf_state_name = 'x_wkf_state'
    _def_wkf_note_name = 'x_wkf_note'

    @api.depends('node_ids')
    def _compute_default_state(self):
        def _get_start_state(nodes):
            if not nodes: return None
            star_id = nodes[0].id
            for n in nodes:
                if n.is_start:
                    star_id = n.id
                    break
            return str(star_id)

        nodes = self.node_ids
        show_nodes = filter(lambda x: x.show_state, nodes)
        no_rest_nodes = filter(lambda x: x.no_reset, nodes)

        self.show_states = ','.join([str(x.id) for x in show_nodes])
        self.default_state = _get_start_state(nodes)
        self.no_reset_states = ','.join(["'%s'" % x.id for x in no_rest_nodes])

    @api.model
    def _default_reset_group(self):
        return self.env['ir.model.data'].xmlid_to_res_id('base.group_system')

    name = fields.Char('Name', required=True, )
    model_id = fields.Many2one('ir.model', 'Module ID', required=True,ondelete="cascade", help="Select a model that you want to create the Workflow")
    model = fields.Char(related='model_id.model', string='Model Name', readonly=True)
    model_view_id = fields.Many2one('ir.ui.view', 'Model  View', help="The form view of the model that want to extend Workflow button on it")
    view_id = fields.Many2one('ir.ui.view', 'Add View', readonly=True, help="The auto created Workflow extend view, show Workflow button, state, logs..", )
    node_ids = fields.One2many('wkf.node', 'wkf_id', 'Node', help='Nodes')
    trans_ids = fields.One2many('wkf.trans', 'wkf_id', 'Transfer', help='Transfers,')
    active = fields.Boolean('Active', default=True)
    field_id = fields.Many2one('ir.model.fields', 'Field Workflow-State', help="The Workflow State field", readonly=True)
    tracking = fields.Integer('Tracking Wkf state', default=1)

    allow_reset = fields.Boolean("Allow to reset the Workflow", default=True, help="If True, This Workflow allow to reset draft")
    reset_group = fields.Many2one('res.groups', "Group Reset", default=_default_reset_group, required=True, help="Workflow Reset Button Groups, default Admin")
    no_reset_states = fields.Char(compute='_compute_default_state', string='No Reset States', help='Which state u can to reset the Workflow')

    default_state = fields.Char(compute='_compute_default_state', string="Default Workflow State value", store=False,
                                help='The default Workflow state, It is come from the star node')
    show_states = fields.Char(compute='_compute_default_state', string="Default  States to display", store=False,
                              help='Which status can show the state widget, It is set by node')

    @api.constrains('model_id')
    def check_uniq(self):
        for one in self:
            if self.search_count([('model_id','=',one.model_id.id)]) > 1:
                raise Warning('workflow must be unique fer model')


    @api.model
    def get_default_state(self, model):
        return self.search([('model', '=', model)]).default_state

    def sync2ref_model(self):
        self.ensure_one()
        self._check()
        self.make_field()
        self.make_view()

    def _check(self):
        if not any([n.is_start for n in self.node_ids]):
            raise Warning('Please check the nodes setting, not found a start node')

    def make_wkf_contain(self):
        wkf_contain = XML(wkf_contain_template)
        wkf_contain.append(self.make_btm_contain())
        wkf_contain.append(XML(wfk_field_state_template % (self.field_id.name, self.show_states)))
        return wkf_contain

    def make_btm_contain(self):
        btn_contain = XML(bton_contain_template)
        for t in self.trans_ids:
            btn = XML(btn_template % {'btn_str': t.name, 'trans_id': t.id, 'vis_state': t.node_from.id})
            if t.group_ids:
                btn.set('groups', t.xml_groups)
            btn_contain.append(btn)

        btn_contain.append(XML(btn_show_log_template % {'btn_str': 'Show Trans Logs', 'btn_grp': 'base.group_user'}))
        btn_contain.append(XML(btn_wkf_reset_template % {'btn_str': 'Reset Workflow', 'btn_grp': 'base.group_system', 'btn_ctx': self.id,
                                                         'no_reset_states': self.no_reset_states}))
        return btn_contain

    def make_view(self):
        self.ensure_one()
        view_obj = self.env['ir.ui.view']
        have_header = '<header>' in self.model_view_id.arch
        arch = have_header and XML(arch_template_header) or XML(arch_template_no_header)
        # wkf_contain = XML("""<div style="background-color:#7B68EE;border-radius:2px;display: inline-block;padding-right: 4px;"></div>""")

        wkf_contain = self.make_wkf_contain()

        arch.insert(0, wkf_contain)

        view_data = {
            'name': '%s.WKF.form.view' % self.model,
            'type': 'form',
            'model': self.model,
            'inherit_id': self.model_view_id.id,
            'mode': 'extension',
            'arch': tostring(arch),
            'priority': 99999,
        }

        # update or create view
        view = self.view_id
        if not view:
            view = view_obj.create(view_data)
            self.write({'view_id': view.id})
        else:
            view.write(view_data)

        return True

    def make_field(self):
        self.ensure_one()
        fd_obj = self.env['ir.model.fields']
        fd_id = fd_obj.search([('name', '=', self._def_wkf_state_name), ('model_id', '=', self.model_id.id)])
        fd_id2 = fd_obj.search([('name', '=', self._def_wkf_note_name), ('model_id', '=', self.model_id.id)])
        fd_data = {
            'name': self._def_wkf_state_name,
            'ttype': 'selection',
            'state': 'manual',
            'model_id': self.model_id.id,
            'model': self.model_id.model,
            'modules': self.model_id.modules,
            'tracking': self.tracking,
            'field_description': u'WorkFollow State',
            # 'select_level': '1',
            'selection': str(self.get_state_selection()),
        }
        if fd_id:
            fd_id.write(fd_data)
        else:
            fd_id = fd_obj.create(fd_data)

        self.write({'field_id': fd_id.id})
        return True

    @api.model
    def get_state_selection(self):
        return [(str(i.id), i.name) for i in self.node_ids]

    def action_no_active(self):
        self.ensure_one()
        self.view_id.unlink()
        self.field_id.unlink()
        # self.active = False
        return True


class wkf_node(models.Model):
    _name = "wkf.node"
    _description = "Wkf Node"
    _order = 'sequence'

    name = fields.Char('Name', required=True, help='A node is basic unit of Workflow')
    sequence = fields.Integer('Sequence')
    code = fields.Char('Code', required=False)
    wkf_id = fields.Many2one('wkf.base', 'Workflow', required=True, index=True, ondelete='cascade')
    split_mode = fields.Selection([('OR', 'Or'), ('AND', 'And')], 'Split Mode', size=3, required=False)
    join_mode = fields.Selection([('OR', 'Or'), ('AND', 'And')], 'Join Mode', size=3, required=True, default='OR',
                                 help='OR:anyone input Transfers approved, will arrived this node.  AND:must all input Transfers approved, will arrived this node')
    # 'kind': fields.selection([('dummy', 'Dummy'), ('function', 'Function'), ('subflow', 'Subflow'), ('stopall', 'Stop All')], 'Kind', required=True),
    action = fields.Char('Python Action', size=64,
                         help='When arrived this node, you can set to trigger a object function to do something, example confirm the order')
    arg = fields.Text('Action Args', size=64, help='the object function args')
    # 'action_id': fields.many2one('ir.actions.server', 'Server Action', ondelete='set null'),
    is_start = fields.Boolean('Workflow Start', help='This node is the start of the Workflow')
    is_stop = fields.Boolean('Workflow Stop', help='This node is the end of the Workflow')
    # 'subflow_id': fields.many2one('workflow', 'Subflow'),
    # 'signal_send': fields.char('Signal (subflow.*)'),
    out_trans = fields.One2many('wkf.trans', 'node_from', 'Out Transfer', help='The out transfer of this node')
    in_trans = fields.One2many('wkf.trans', 'node_to', 'Incoming Transfer', help='The input transfer of this node')
    show_state = fields.Boolean('Show In Workflow', default=True, help="If True, This node will show in Workflow states")
    no_reset = fields.Boolean('Invisible Reset', default=True, help="If True, this Node not display the Reset button, default is True")
    event_need = fields.Boolean('Create event', help="If true, When Workflow arrived this node, will create a calendar event relation users")
    event_users = fields.Many2many('res.users', 'event_users_trans_ref', 'tid', 'uid', 'Event Users', help="The calendar event users")

    def backward_cancel_logs(self, res_id):
        """
        cancel the logs from this node, and create_date after the logs
        """
        log_obj = self.env['log.wkf.trans']
        logs = log_obj.search([('res_id', '=', res_id), ('trans_id.node_from.id', '=', self.id)])
        if logs:
            min_date = min([x.create_date for x in logs])
            logs2 = log_obj.search([('res_id', '=', res_id), ('create_date', '>=', min_date)])
            logs.write({'active': False})
            logs2.write({'active': False})

    def check_trans_in(self, res_id):
        self.ensure_one()

        flag = True
        join_mode = self.join_mode
        log_obj = self.env['log.wkf.trans']

        flag = False
        if join_mode == 'OR':
            flag = True
        else:
            in_trans = filter(lambda x: x.is_backward is False, self.in_trans)
            trans_ids = [x.id for x in in_trans]
            logs = log_obj.search([('res_id', '=', res_id), ('trans_id', 'in', trans_ids)])
            log_trans_ids = [x.trans_id.id for x in logs]
            flag = set(trans_ids) == set(log_trans_ids) and True or False

        return flag



    def make_event(self, name):
        data = {
            'name': '%s %s' % (name, self.name),
            'state': 'open',  # to block that meeting date in the calendar
            'partner_ids': [(6, 0, [u.partner_id.id for u in self.event_users])],
            'start': fields.Datetime.now(),
            'stop': fields.Datetime.now(),
            'start_datetime': fields.Datetime.now(),
            'stop_datetime': fields.Datetime.now(),
            'duration': 1,
            'alarm_ids': [(6, 0, [1])],
        }
        self.env['calendar.event'].create(data)
        return True


class wkf_trans(models.Model):
    _name = "wkf.trans"
    _description = "Wkf Trans"
    _order = "sequence"

    @api.depends('group_ids')
    def _compute_xml_groups(self):
        data_obj = self.env['ir.model.data']
        xml_ids = []
        for g in self.group_ids:
            data = data_obj.search([('res_id', '=', g.id), ('model', '=', 'res.groups')])
            xml_ids.append(data.complete_name)
        self.xml_groups = xml_ids and ','.join(xml_ids) or False

    name = fields.Char("Name", required=True, help='A transfer is from a node to other node')
    code = fields.Char('Code', required=False)
    group_ids = fields.Many2many('res.groups', 'group_trans_ref', 'tid', 'gid', 'Groups', help="The groups who can process this transfer")
    condition = fields.Char('Condition', required=True, default='True', help='The check condition of this transfer, default is True')
    node_from = fields.Many2one('wkf.node', 'From Node', required=True, index=True, ondelete='cascade', )
    node_to = fields.Many2one('wkf.node', 'TO Node', required=True, index=True, ondelete='cascade')
    wkf_id = fields.Many2one('wkf.base', related='node_from.wkf_id', store=True)
    model = fields.Char(related='wkf_id.model')
    xml_groups = fields.Char(compute='_compute_xml_groups', string='XML Groups')
    is_backward = fields.Boolean(u'Is Reverse', help="Is a Reverse transfer")
    auto = fields.Boolean(u'Auto', help="If true, when condition is True,transfer will auto finish, not need button, default false")
    sequence = fields.Integer('Sequence')
    need_note = fields.Boolean('Force note', help="If true, the Workflow note can not be empty, usually when transfer is Reverse,you need it")

    def make_log(self, res_name, res_id, note=''):
        return self.env['log.wkf.trans'].create({'name': res_name, 'res_id': res_id, 'trans_id': self.id, 'note': note})


class log_wkf_trans(models.Model):
    _name = "log.wkf.trans"
    _description = "Wkf log"

    name = fields.Char('Name')
    trans_id = fields.Many2one('wkf.trans', 'Transfer')
    model = fields.Char(related='trans_id.model', string='Model')
    res_id = fields.Integer('Resource ID')
    active = fields.Boolean('Active', default=True)
    note = fields.Text('Note', help="If you want record something for this transfer, write here")
