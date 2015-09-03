# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import OperationalError

import openerp
from openerp import api, fields, models
from openerp.tools.translate import _
from openerp.exceptions import UserError
import openerp.addons.decimal_precision as dp

PROCUREMENT_PRIORITIES = [('0', 'Not urgent'), ('1', 'Normal'), ('2', 'Urgent'), ('3', 'Very Urgent')]


class ProcurementGroup(models.Model):
    '''
    The procurement group class is used to group products together
    when computing procurements. (tasks, physical products, ...)

    The goal is that when you have one sale order of several products
    and the products are pulled from the same or several location(s), to keep
    having the moves grouped into pickings that represent the sale order.

    Used in: sales order (to group delivery order lines like the so), pull/push
    rules (to pack like the delivery order), on orderpoints (e.g. for wave picking
    all the similar products together).

    Grouping is made only if the source and the destination is the same.
    Suppose you have 4 lines on a picking from Output where 2 lines will need
    to come from Input (crossdock) and 2 lines coming from Stock -> Output As
    the four procurement orders will have the same group ids from the SO, the
    move from input will have a stock.picking with 2 grouped lines and the move
    from stock will have 2 grouped lines also.

    The name is usually the name of the original document (sale order) or a
    sequence computed if created manually.
    '''
    _name = 'procurement.group'
    _description = 'Procurement Requisition'
    _order = "id desc"

    name = fields.Char(string='Reference', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('procurement_group') or '')
    move_type = fields.Selection([('direct', 'Partial'), ('one', 'All at once')], string='Delivery Type', required=True, default=lambda self: 'direct')
    procurement_ids = fields.One2many('procurement.order', 'group_id', string='Procurements')


class ProcurementRule(models.Model):
    '''
    A rule describe what a procurement should do; produce, buy, move, ...
    '''
    _name = 'procurement.rule'
    _description = "Procurement Rule"
    _order = "name"

    @api.model
    def _get_action(self):
        return []

    name = fields.Char(required=True, translate=True, help="This field will fill the packing origin and the name of its moves")
    active = fields.Boolean(help="If unchecked, it will allow you to hide the rule without removing it.", default=True)
    group_propagation_option = fields.Selection([('none', 'Leave Empty'), ('propagate', 'Propagate'), ('fixed', 'Fixed')], string="Propagation of Procurement Group", default='propagate')
    group_id = fields.Many2one('procurement.group', string='Fixed Procurement Group')
    action = fields.Selection(selection=lambda s: s._get_action(), required=True)
    sequence = fields.Integer(default=20)
    company_id = fields.Many2one('res.company', string='Company')


class ProcurementOrder(models.Model):
    """
    Procurement Orders
    """
    _name = "procurement.order"
    _description = "Procurement"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'priority desc, date_planned, id asc'
    _log_create = False

    name = fields.Text(string='Description', required=True)
    origin = fields.Char(string='Source Document', help="Reference of the document that created this Procurement. This is automatically completed by Odoo.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    # These two fields are used for shceduling
    priority = fields.Selection(PROCUREMENT_PRIORITIES, required=True, select=True, track_visibility='onchange', default='1')
    date_planned = fields.Datetime(string='Scheduled Date', required=True, default=fields.Datetime.now(), select=True, track_visibility='onchange')
    group_id = fields.Many2one('procurement.group', string='Procurement Group')
    rule_id = fields.Many2one('procurement.rule', string='Rule', track_visibility='onchange', help="Chosen rule for the procurement resolution. Usually chosen by the system but can be manually set by the procurement manager to force an unusual behavior.")
    product_id = fields.Many2one('product.product', string='Product', required=True, states={'confirmed': [('readonly', False)]}, readonly=True)
    product_qty = fields.Float(string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, states={'confirmed': [('readonly', False)]}, readonly=True)
    product_uom = fields.Many2one('product.uom', string='Product Unit of Measure', required=True, states={'confirmed': [('readonly', False)]}, readonly=True)
    state = fields.Selection([('cancel', 'Cancelled'), ('confirmed', 'Confirmed'), ('exception', 'Exception'), ('running', 'Running'), ('done', 'Done')], string='Status', required=True, track_visibility='onchange', copy=False, default='confirmed')

    @api.model
    def _needaction_domain_get(self):
        return [('state', '=', 'exception')]

    @api.multi
    def unlink(self):
        unlink_ids = self.filtered(lambda procurements: procurements.state == 'cancel')
        for s in (self-unlink_ids):
            if s.state != 'cancel':
                raise UserError(_('Cannot delete Procurement Order(s) which are in %s state.') % s.state)
        return super(ProcurementOrder, unlink_ids).unlink()

    @api.model
    def create(self, vals):
        procurement = super(ProcurementOrder, self).create(vals)
        if not self._context.get('procurement_autorun_defer'):
            procurement.run()
        return procurement

    @api.multi
    def do_view_procurements(self):
        '''
        This function returns an action that display existing procurement orders
        of same procurement group of given ids.
        '''
        result = self.env['ir.actions.act_window'].for_xml_id('procurement', 'do_view_procurements')
        group_ids = set([proc.group_id.id for proc in self if proc.group_id])
        result['domain'] = "[('group_id','in',[" + ','.join(map(str, list(group_ids))) + "])]"
        return result

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product.
        """
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    @api.multi
    def get_cancel_ids(self):
        return [proc.id for proc in self if proc.state != 'done']

    @api.multi
    def cancel(self):
        # cancel only the procurements that aren't done already
        to_cancel_ids = self.get_cancel_ids()
        if to_cancel_ids:
            return self.browse(to_cancel_ids).write({'state': 'cancel'})

    @api.multi
    def reset_to_confirmed(self):
        return self.write({'state': 'confirmed'})

    @api.multi
    def run(self, autocommit=False):
        for procurement in self:
            if procurement.state not in ("running", "done"):
                try:
                    if procurement._assign():
                        res = procurement._run()
                        if res:
                            procurement.write({'state': 'running'})
                        else:
                            procurement.write({'state': 'exception'})
                    else:
                        procurement.message_post(body=_('No rule matching this procurement'))
                        procurement.write({'state': 'exception'})
                    if autocommit:
                        self._cr.commit()
                except OperationalError:
                    if autocommit:
                        self._cr.rollback()
                        continue
                    else:
                        raise
        return True

    @api.multi
    def check(self, autocommit=False):
        done_procs = self.env['procurement.order']
        for procurement in self:
            try:
                result = procurement._check()
                if result:
                    done_procs |= procurement
                if autocommit:
                    self._cr.commit()
            except OperationalError:
                if autocommit:
                    self._cr.rollback()
                    continue
                else:
                    raise
        if done_procs:
            done_procs.write({'state': 'done'})
        return done_procs

    # Method to overwrite in different procurement modules
    @api.multi
    def _find_suitable_rule(self):
        '''This method returns a procurement.rule that depicts what to do with the given procurement
        in order to complete its needs. It returns False if no suiting rule is found.
            :param procurement: browse record
            :rtype: int or False
        '''
        return False

    @api.multi
    def _assign(self):
        '''This method check what to do with the given procurement in order to complete its needs.
        It returns False if no solution is found, otherwise it stores the matching rule (if any) and
        returns True.'''
        # if the procurement already has a rule assigned, we keep it (it has a higher priority as it may have been chosen manually)
        if self.rule_id:
            return True
        elif self.product_id.type not in ('service', 'digital'):
            rule_id = self._find_suitable_rule()
            if rule_id:
                self.write({'rule_id': rule_id})
                return True
        return False

    @api.multi
    def _run(self):
        '''This method implements the resolution of the given procurement
            :returns: True if the resolution of the procurement was a success, False otherwise to set it in exception
        '''
        return True

    @api.multi
    def _check(self):
        '''Returns True if the given procurement is fulfilled, False otherwise
            :param procurement: browse record
            :rtype: boolean
        '''
        return False

    # Scheduler
    @api.model
    def run_scheduler(self, use_new_cursor=False, company_id=False):
        try:
            if use_new_cursor:
                cr = openerp.registry(self._cr.dbname).cursor()

            # Run confirmed procurements
            dom = [('state', '=', 'confirmed')]
            if company_id:
                dom += [('company_id', '=', company_id)]
            prev_ids = []
            while True:
                ids = self.sudo().search(dom)
                if not ids or prev_ids == ids:
                    break
                else:
                    prev_ids = ids
                ids.sudo().run(autocommit=use_new_cursor)
                if use_new_cursor:
                    cr.commit()

            # Check if running procurements are done
            offset = 0
            dom = [('state', '=', 'running')]
            if company_id:
                dom += [('company_id', '=', company_id)]
            prev_ids = []
            while True:
                ids = self.sudo().search(dom, offset=offset)
                if not ids or prev_ids == ids:
                    break
                else:
                    prev_ids = ids
                ids.sudo().check(autocommit=use_new_cursor)
                if use_new_cursor:
                    cr.commit()

        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass

        return {}
