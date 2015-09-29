# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from openerp.exceptions import UserError
from openerp.tools.translate import _
from openerp import api, fields, models

#----------------------------------------------------------
# Work Centers
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle


class MrpProductionWorkcenterLine(models.Model):

    @api.depends('hour', 'date_planned')
    def _get_date_end(self):
        """ Finds ending date.
        @return: Dictionary of values.
        """
        for operation in self:
            if operation.date_planned:
                intervals = self.env['resource.calendar'].interval_get_multi(
                    [(operation.date_planned, operation.hour, operation.workcenter_id.calendar_id.id)])
                interval = intervals.get(
                    (operation.date_planned, operation.hour, operation.workcenter_id.calendar_id.id))
                if interval:
                    operation.date_planned_end = fields.Datetime.to_string(interval[-1][1])
                else:
                    operation.date_planned_end = operation.date_planned

    @api.onchange('production_id')
    def onchange_production_id(self):
        self.product = self.production_id.product_id.id
        self.uom = self.production_id.product_uom.id
        self.qty = self.production_id.product_qty

    _inherit = 'mrp.production.workcenter.line'
    _order = "sequence, date_planned"

    state = fields.Selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('pause', 'Pending'), ('startworking', 'In Progress'), ('done', 'Finished')], 'Status', readonly=True, copy=False, default='draft',
                             help="* When a work order is created it is set in 'Draft' status.\n"
                             "* When user sets work order in start mode that time it will be set in 'In Progress' status.\n"
                                  "* When work order is in running mode, during that time if user wants to stop or to make changes in order then can set in 'Pending' status.\n"
                                  "* When the user cancels the work order it will be set in 'Canceled' status.\n"
                                  "* When order is completely processed that time it is set in 'Finished' status.")
    date_planned = fields.Datetime('Scheduled Date', select=True)
    date_planned_end = fields.Datetime(compute="_get_date_end", string='End Date')
    date_start = fields.Datetime('Start Date')
    date_finished = fields.Datetime('End Date')
    delay = fields.Float('Working Hours', help="The elapsed time between operation start and stop in this Work Center", readonly=True, default=0.0)
    production_state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Waiting Goods'), ('ready', 'Ready to Produce'), (
        'in_production', 'In Production'), ('cancel', 'Canceled'), ('done', 'Done')], String='Production Status', readonly=True, related='production_id.state', default='draft')
    product = fields.Many2one(comodel_name='product.product', related='production_id.product_id', string='Product',
                              readonly=True)
    qty = fields.Float(String='Qty', readonly=True, related='production_id.product_qty', store=True)
    uom = fields.Many2one(comodel_name='product.uom', related='production_id.product_uom', string='Unit of Measure', readonly=True)

    @api.multi
    def modify_production_order_state(self, action):
        """ Modifies production order state if work order state is changed.
        @param action: Action to perform.
        @return: Nothing
        """
        MrpProduction = self.env['mrp.production']
        if action == 'start':
            if self.production_id.state == 'confirmed':
                self.production_id.force_production()
                self.production_id.signal_workflow('button_produce')
            elif self.production_id.state == 'ready':
                self.production_id.signal_workflow('button_produce')
            elif self.production_id.state == 'in_production':
                return
            else:
                raise UserError(_('Manufacturing order cannot be started in state "%s"!') % (self.production_id.state,))
        else:
            open_count = self.search_count([('production_id', '=', self.production_id.id), ('state', '!=', 'done')])
            flag = not bool(open_count)
            if flag:
                for production in self.production_id:
                    if production.move_lines or production.move_created_ids:
                        MrpProduction.action_produce(production.id, production.product_qty, 'consume_produce')
                MrpProduction.signal_workflow('button_produce_done')

    @api.multi
    def write(self, vals, update=True):
        result = super(MrpProductionWorkcenterLine, self).write(vals)
        MrpProduction = self.env['mrp.production']
        if vals.get('date_planned', False) and update:
            for production in self:
                if production.production_id.workcenter_lines:
                    dstart = min(vals['date_planned'], production.production_id.workcenter_lines[0]['date_planned'])
                    MrpProduction.write({'date_start': dstart}, mini=False)
        return result

    @api.multi
    def action_draft(self):
        """ Sets state to draft.
        @return: True
        """
        return self.write({'state': 'draft'})

    @api.multi
    def action_start_working(self):
        """ Sets state to start working and writes starting date.
        @return: True
        """
        self.modify_production_order_state('start')
        self.write({'state': 'startworking', 'date_start': fields.Datetime.now()})
        return True

    @api.multi
    def action_done(self):
        """ Sets state to done, writes finish date and calculates delay.
        @return: True
        """
        delay = 0.0
        date_now = fields.Datetime.now()
        date_start = fields.Datetime.from_string(self.date_start)
        date_finished = fields.Datetime.from_string(date_now)
        delay += (date_finished-date_start).days * 24
        delay += (date_finished-date_start).seconds / float(60*60)
        self.write({'state': 'done', 'date_finished': date_now, 'delay': delay})
        self.modify_production_order_state('done')
        return True

    @api.multi
    def action_cancel(self):
        """ Sets state to cancel.
        @return: True
        """
        return self.write({'state': 'cancel'})

    @api.multi
    def action_pause(self):
        """ Sets state to pause.
        @return: True
        """
        return self.write({'state': 'pause'})

    @api.multi
    def action_resume(self):
        """ Sets state to startworking.
        @return: True
        """
        return self.write({'state': 'startworking'})


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    allow_reorder = fields.Boolean('Free Serialisation', help="Check this to be able to move independently all production orders, without moving dependent ones.")

    @api.multi
    def _production_date_end(self):
        """ Calculates planned end date of production order.
        @return: Dictionary of values
        """
        for production in self:
            for line in production.workcenter_lines:
                production.date_planned = max(line.date_planned_end, production.date_planned)

    @api.multi
    def action_production_end(self):
        """ Finishes work order if production order is done.
        @return: Super method
        """
        for workcenter_line in self.workcenter_lines:
            if workcenter_line.state == 'draft':
                workcenter_line.signal_workflow('button_start_working')
            workcenter_line.signal_workflow('button_done')
        return super(MrpProduction, self).action_production_end()

    @api.multi
    def action_in_production(self):
        """ Changes state to In Production and writes starting date.
        @return: True
        """
        for production in self:
            if production.workcenter_lines:
                production.workcenter_lines[0].signal_workflow('button_start_working')
        return super(MrpProduction, self).action_in_production()

    @api.multi
    def action_cancel(self):
        """ Cancels work order if production order is canceled.
        @return: Super method
        """
        MrpProductionWorkcenterLine = self.env['mrp.production.workcenter.line']
        MrpProductionWorkcenterLine.signal_workflow('button_cancel')
        return super(MrpProduction, self).action_cancel()

    @api.multi
    def _compute_planned_workcenter(self, mini=False):
        """ Computes planned and finished dates for work order.
        @return: Calculated date
        """
        date_end = datetime.now()
        for production in self:
            date_end = fields.Datetime.from_string(production.date_planned)
            if not production.date_start:
                production.write(
                    {'date_start': production.date_planned}, update=False)
            old = None
            for wci in range(len(production.workcenter_lines)):
                wc = production.workcenter_lines[wci]
                if (old is None) or (wc.sequence > old):
                    dt = date_end
                if (wc.date_planned < fields.Datetime.to_string(dt)) or mini:
                    production.workcenter_lines.write({
                        'date_planned': fields.Datetime.to_string(dt)})
                    interval = self.env['resource.calendar'].interval_get(
                        wc.workcenter_id.calendar_id and wc.workcenter_id.calendar_id.id or None, dt, wc.hour or 0.0)
                    if interval:
                        date_end = max(date_end, interval[-1][1])
                else:
                    date_end = fields.Datetime.from_string(
                        wc.date_planned_end)
                old = wc.sequence or 0
            super(MrpProduction, self).write(
                {'date_finished': date_end})
        return date_end

    @api.multi
    def _move_pass(self):
        """ Calculates start date for stock moves finding interval from resource calendar.
        @return: True
        """
        for production in self:
            if production.allow_reorder:
                continue
            todo = list(production.move_lines)
            date = fields.Datetime.from_string(production.date_start)
            while todo:
                l = todo.pop(0)
                if l.state in ('done', 'cancel', 'draft'):
                    continue
                todo += l.move_dest_id_lines
                if l.production_id.state and (l.production_id.date_finished > date):
                    if l.production_id.state not in ('done', 'cancel'):
                        for wc in l.production_id.workcenter_lines:
                            interval = self.env['resource.calendar'].interval_min_get(wc.workcenter_id.calendar_id.id or False, date, wc.hour or 0.0)
                            date = interval[0][0]
                        if l.production_id.date_start > fields.Datetime.from_string(date):
                            self.write({'date_start': fields.Datetime.from_string(date)}, mini=True)
        return True

    @api.multi
    def _move_futur(self):
        """ Calculates start date for stock moves.
        @return: True
        """
        for production in self:
            if production.allow_reorder:
                continue
            for line in production.move_created_ids:
                l = line
                while l.move_dest_id:
                    l = l.move_dest_id
                    if l.state in ('done', 'cancel', 'draft'):
                        break
                    if l.production_id.state in ('done', 'cancel'):
                        break
                    if l.production_id and (l.production_id.date_start < production.date_finished):
                        self.write({'date_start': production.date_finished})
                        break
        return True

    @api.multi
    def write(self, vals, update=True, mini=True):
        direction = {}
        if vals.get('date_start', False):
            for production in self:
                direction[production.id] = cmp(production.date_start, vals.get('date_start', False))
        result = super(MrpProduction, self).write(vals)
        if (vals.get('workcenter_lines', False) or vals.get('date_start', False) or vals.get('date_planned', False)) and update:
            self._compute_planned_workcenter(mini=mini)
        for d in direction:
            if direction[d] == 1:
                # the production order has been moved to the passed
                self._move_pass()
                pass
            elif direction[d] == -1:
                self._move_futur()
                # the production order has been moved to the future
                pass
        return result

    @api.multi
    def action_compute(self, properties=None):
        """ Computes bills of material of a product and planned date of work order.
        @param properties: List containing dictionaries of properties.
        @return: No. of products.
        """
        result = super(MrpProduction, self).action_compute(properties=properties)
        self._compute_planned_workcenter()
        return result
