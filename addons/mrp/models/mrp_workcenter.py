# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _

# ----------------------------------------------------------
# Work Centers
# ----------------------------------------------------------


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource': "resource_id"}


    note = fields.Text(string='Description', help="Description of the Work Center. ")
    capacity = fields.Float(string='Capacity', default=1.0, help="Number of pieces work center can produce in parallel.")
    time_start = fields.Float(string='Time before prod.', help="Time in minutes for the setup.")
    sequence = fields.Integer(required=True, default=1, help="Gives the sequence order when displaying a list of work centers.")
    time_stop = fields.Float(string='Time after prod.', help="Time in minutes for the cleaning.")
    resource_id = fields.Many2one('resource.resource', string='Resource', ondelete='cascade', required=True)
    order_ids = fields.One2many('mrp.production.work.order', 'workcenter_id', string="Orders")
    routing_line_ids = fields.One2many('mrp.routing.workcenter', 'workcenter_id', "Routing Lines")
    nb_orders = fields.Integer('Computed Orders', compute='_compute_orders')
    color = fields.Integer('Color')
    count_ready_order = fields.Integer(compute='_compute_orders', string="Total Ready Orders")
    count_progress_order = fields.Integer(compute='_compute_orders', string="Total Running Orders")
    blocked = fields.Boolean('Blocked')
    working_state = fields.Selection([('normal', 'Normal'), ('blocked', 'Blocked'), ('done', 'In Progress')], string='Status', default="normal", store=True, 
                                compute="_compute_working_state", inverse='_set_blocked')
    oee = fields.Float(compute='_compute_oee', help='Overall Equipment Efficiency')
    blocked_time = fields.Float(compute='_compute_oee', help='Number of blocked hours on the last 30 days')
    blocked_time_ids = fields.One2many('mrp.workcenter.blocked.time', 'workcenter_id', string='Blocked Times')

    @api.one
    def _set_blocked(self):
        if self.working_state == 'blocked':
            self[0].block(False, "")
        elif self.blocked:
            self[0].unblock()

    @api.depends('blocked')
    def _compute_oee(self):
        for workcenter in self:
            workcenter.blocked_time = sum(workcenter.blocked_time_ids.filtered(lambda x: fields.Datetime.from_string(x.date_start).month == fields.datetime.now().month).mapped('duration'))
            timesheet_hours = 0.0
            for order in workcenter.order_ids:
                timesheet_hours += sum(order.time_ids.mapped('duration'))
            if workcenter.blocked_time > 0:
                workcenter.oee = workcenter.blocked_time / (workcenter.blocked_time + timesheet_hours)

    @api.multi
    @api.depends('order_ids', 'order_ids.state', 'blocked')
    def _compute_working_state(self):
        for workcenter in self:
            if workcenter.blocked:
                workcenter.working_state = 'blocked'
                continue
            if workcenter.count_progress_order:
                workcenter.working_state = 'done'
            else:
                workcenter.working_state = 'normal'

    @api.multi
    def block(self, reason, description):
        self.ensure_one()
        if not self.blocked:
            time_obj = self.env['mrp.workcenter.blocked.time']
            time_obj.create({'workcenter_id': self.id,
                             'description': description,
                             'reason_id': reason and reason.id or False,
                             'date_start': fields.Datetime.now(),
                             })
            #Stop all timers
            self.order_ids.end_all()
            self.write({'blocked': True})

    @api.multi
    def unblock(self):
        self.ensure_one()
        if self.blocked:
            times = self.env['mrp.workcenter.blocked.time'].search([('workcenter_id', '=', self.id), ('state', '=', 'running')])
            times.write({'state': 'done', 'date_end': fields.Datetime.now()})
        self.write({'blocked': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': self.env.ref('base.menu_mrp_root').id},
        }


    @api.depends('order_ids')
    def _compute_orders(self):
        WorkcenterLine = self.env['mrp.production.work.order']
        for workcenter in self:
            workcenter.nb_orders = WorkcenterLine.search_count([('workcenter_id', '=', workcenter.id), ('state', '!=', 'done')]) #('state', 'in', ['pending', 'startworking'])
            workcenter.count_ready_order = WorkcenterLine.search_count([('workcenter_id', '=', workcenter.id), ('state', '=', 'ready')])
            workcenter.count_progress_order = WorkcenterLine.search_count([('workcenter_id', '=', workcenter.id), ('state', '=', 'progress')])

    @api.multi
    @api.constrains('capacity')
    def _check_capacity(self):
        for obj in self:
            if obj.capacity <= 0.0:
                raise ValueError(_('The capacity must be strictly positive.'))


class MrpWorkcenterBlockReason(models.Model):
    _name = "mrp.workcenter.block.reason"
    _description = "Workcenter Blocking Reason"

    name = fields.Char("Reason")


class MrpWorkcenterBlockedTimeLine(models.Model):
    _name = "mrp.workcenter.blocked.time"

    @api.depends('date_end')
    def _compute_duration(self):
        for blocktime in self:
            if blocktime.date_end:
                diff = fields.Datetime.from_string(blocktime.date_end) - fields.Datetime.from_string(blocktime.date_start)
                blocktime.duration = round(diff.total_seconds() / 60.0 / 60.0, 2)

    workcenter_id = fields.Many2one('mrp.workcenter', required=True)
    reason_id = fields.Many2one('mrp.workcenter.block.reason')
    description = fields.Text('Description')
    date_start = fields.Datetime('Start Date')
    date_end = fields.Datetime('End Date')
    duration = fields.Float('Duration', compute='_compute_duration')
    state = fields.Selection([('running', 'Running'), ('done', 'Done')], string="Status", default="running")
