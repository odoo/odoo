# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class OperationCode(models.Model):
    _name = "mrp_operations.operation.code"

    name = fields.Char('Operation Name', required=True)
    code = fields.Char('Code', size=16, required=True)
    start_stop = fields.Selection([
        ('start', 'Start'),
        ('pause', 'Pause'),
        ('resume', 'Resume'),
        ('cancel', 'Cancelled'),
        ('done', 'Done')], string='Status', required=True)


class Operation(models.Model):
    _name = "mrp_operations.operation"

    production_id = fields.Many2one('mrp.production', 'Production', required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', required=True)
    code_id = fields.Many2one('mrp_operations.operation.code', 'Code', required=True)
    date_start = fields.Datetime('Start Date', default=fields.Datetime.now)
    date_finished = fields.Datetime('End Date')
    # TDE FIXME: was a date
    order_date = fields.Datetime(
        'Order Date', related='production_id.date_planned', store=True)

    def create(self, cr, uid, vals, context=None):
        workcenter_pool = self.pool.get('mrp.production.workcenter.line')
        code_ids=self.pool.get('mrp_operations.operation.code').search(cr,uid,[('id','=',vals['code_id'])])
        code=self.pool.get('mrp_operations.operation.code').browse(cr, uid, code_ids, context=context)[0]
        wc_op_id=workcenter_pool.search(cr,uid,[('workcenter_id','=',vals['workcenter_id']),('production_id','=',vals['production_id'])])
        if code.start_stop in ('start','done','pause','cancel','resume'):
            if not wc_op_id:
                production_obj=self.pool.get('mrp.production').browse(cr, uid, vals['production_id'], context=context)
                wc_op_id.append(workcenter_pool.create(cr,uid,{'production_id':vals['production_id'],'name':production_obj.product_id.name,'workcenter_id':vals['workcenter_id']}))
            if code.start_stop=='start':
                workcenter_pool.action_start_working(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_start_working')

            if code.start_stop=='done':
                workcenter_pool.action_done(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_done')
                self.pool.get('mrp.production').write(cr,uid,vals['production_id'],{'date_finished':datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

            if code.start_stop=='pause':
                workcenter_pool.action_pause(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_pause')

            if code.start_stop=='resume':
                workcenter_pool.action_resume(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_resume')

            if code.start_stop=='cancel':
                workcenter_pool.action_cancel(cr,uid,wc_op_id)
                workcenter_pool.signal_workflow(cr, uid, [wc_op_id[0]], 'button_cancel')

        caca_id = super(Operation, self).create(cr, uid, vals, context=context)
        caca = self.browse(cr, uid, [caca_id], context=context)

        if not caca.check_operation():
            return
        delay=caca.calc_delay()
        line_vals = {}
        line_vals['delay'] = delay
        if vals.get('date_start',False):
            if code.start_stop == 'done':
                line_vals['date_finished'] = vals['date_start']
            elif code.start_stop == 'start':
                line_vals['date_start'] = vals['date_start']

        self.pool.get('mrp.production.workcenter.line').write(cr, uid, wc_op_id, line_vals, context=context)

        return caca_id

    @api.multi
    def write(self, vals):
        res = super(Operation, self).write(vals)

        if 'code_id' in vals:
            self.check_operation()

        if 'date_start' in vals:
            for operation in self:
                delay = operation.calc_delay(vals['date_start'])
                self.env['mrp.production.workcenter.line'].search([
                    ('workcenter_id', '=', operation.workcenter_id.id),
                    ('production_id', '=', operation.production_id.id)]
                ).write({'delay': delay})
        return res

    @api.multi
    def calc_delay(self, date_start):
        """ Calculates delay of work order.
        @return: Delay
        """
        code_list = []
        for operation in self.search([('production_id', '=', self.production_id.id), ('workcenter_id', '=', self.workcenter_id.id)]):
            code_list.append((operation.code_id.start_stop, operation.date_start))

        code_list.append((self.env['mrp_operations.operation.code'].browse(self.code_id.id).start_stop, date_start))
        diff = 0
        for idx, (code, date_start) in enumerate(code_list):
            if not idx:
                continue
            if code.start_stop in ('pause', 'done', 'cancel'):
                if code_list[idx-1].start_stop not in ('resume', 'start'):
                    continue
                date_a = datetime.strptime(code_list[idx-1][1], tools.DEFAULT_SERVER_DATETIME_FORMAT)
                date_b = datetime.strptime(date_start, tools.DEFAULT_SERVER_DATETIME_FORMAT)
                delta = date_b - date_a
                diff += delta.total_seconds() / float(60*60)
        return diff

    @api.one
    def check_operation(self):
        """ Finds which operation is called ie. start, pause, done, cancel.
        @return: True or raise
        """
        code = self.code_id
        operations = self.search([
            ('production_id', '=', self.production_id.id),
            ('workcenter_id', '=', self.workcenter_id.id)])

        if not operations:
            if code.start_stop != 'start':
                raise UserError(_('Operation is not started yet!'))
        else:
            code_list = [operation.code_id.start_stop for operation in operations]
            if code.start_stop == 'start':
                if 'start' in code_list:
                    raise UserError(_('Operation has already started! You can either Pause/Finish/Cancel the operation.'))

            if code.start_stop == 'pause':
                if code_list[-1] not in ('resume', 'start'):
                    raise UserError(_('In order to Pause the operation, it must be in the Start or Resume state!'))

            if code.start_stop == 'resume':
                if code_list[-1] != 'pause':
                    raise UserError(_('In order to Resume the operation, it must be in the Pause state!'))

            if code.start_stop == 'done':
                if code_list[-1] not in ('start', 'done'):
                    raise UserError(_('In order to Finish the operation, it must be in the Start or Resume state!'))
                if 'cancel' in code_list:
                    raise UserError(_('Operation is Already Cancelled!'))

            if code.start_stop == 'cancel':
                if 'start' not in code_list:
                    raise UserError(_('No operation to cancel.'))
                if 'done' in code_list:
                    raise UserError(_('Operation is already finished!'))

        return True

    @api.model
    def initialize_workflow_instance(self):
        self.env['mrp.production.workcenter.line'].search([]).create_workflow
        return True
