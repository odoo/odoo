# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import OperationalError

from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError

import odoo.addons.decimal_precision as dp

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

    name = fields.Char(
        'Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('procurement.group') or '',
        required=True)
    move_type = fields.Selection([
        ('direct', 'Partial'),
        ('one', 'All at once')], string='Delivery Type', default='direct',
        required=True)
    procurement_ids = fields.One2many('procurement.order', 'group_id', 'Procurements')


class ProcurementRule(models.Model):
    ''' A rule describe what a procurement should do; produce, buy, move, ... '''
    _name = 'procurement.rule'
    _description = "Procurement Rule"
    _order = "name"

    name = fields.Char(
        'Name', required=True, translate=True,
        help="This field will fill the packing origin and the name of its moves")
    active = fields.Boolean(
        'Active', default=True,
        help="If unchecked, it will allow you to hide the rule without removing it.")
    group_propagation_option = fields.Selection([
        ('none', 'Leave Empty'),
        ('propagate', 'Propagate'),
        ('fixed', 'Fixed')], string="Propagation of Procurement Group", default='propagate')
    group_id = fields.Many2one('procurement.group', 'Fixed Procurement Group')
    action = fields.Selection(
        selection='_get_action', string='Action',
        required=True)
    sequence = fields.Integer('Sequence', default=20)
    company_id = fields.Many2one('res.company', 'Company')

    @api.model
    def _get_action(self):
        return []


class ProcurementOrder(models.Model):
    """ Procurement Orders """
    _name = "procurement.order"
    _description = "Procurement"
    _order = 'priority desc, date_planned, id asc'
    _inherit = ['mail.thread','ir.needaction_mixin']


    name = fields.Text('Description', required=True)

    origin = fields.Char('Source Document', help="Reference of the document that created this Procurement. This is automatically completed by Odoo.")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('procurement.orer'),
        required=True)
    # These two fields are used for scheduling
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='1',
        required=True, index=True, track_visibility='onchange')
    date_planned = fields.Datetime(
        'Scheduled Date', default=fields.Datetime.now,
        required=True, index=True, track_visibility='onchange')

    group_id = fields.Many2one('procurement.group', 'Procurement Group')
    rule_id = fields.Many2one(
        'procurement.rule', 'Rule',
        track_visibility='onchange',
        help="Chosen rule for the procurement resolution. Usually chosen by the system but can be manually set by the procurement manager to force an unusual behavior.")

    product_id = fields.Many2one(
        'product.product', 'Product',
        readonly=True, required=True,
        states={'confirmed': [('readonly', False)]})
    product_qty = fields.Float(
        'Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True, required=True,
        states={'confirmed': [('readonly', False)]})
    product_uom = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        readonly=True, required=True,
        states={'confirmed': [('readonly', False)]})
    state = fields.Selection([
        ('cancel', 'Cancelled'),
        ('confirmed', 'Confirmed'),
        ('exception', 'Exception'),
        ('running', 'Running'),
        ('done', 'Done')], string='Status', default='confirmed',
        copy=False, required=True, track_visibility='onchange')

    @api.model
    def _needaction_domain_get(self):
        return [('state', '=', 'exception')]

    @api.model
    def create(self, vals):
        procurement = super(ProcurementOrder, self).create(vals)
        if not self._context.get('procurement_autorun_defer'):
            procurement.run()
        return procurement

    @api.multi
    def unlink(self):
        if any(procurement.state == 'cancel' for procurement in self):
            raise UserError(_('You cannot delete procurements that are in cancel state.'))
        return super(ProcurementOrder, self).unlink()

    @api.multi
    def do_view_procurements(self):
        '''
        This function returns an action that display existing procurement orders
        of same procurement group of given ids.
        '''
        action = self.env.ref('procurement.do_view_procurements').read()[0]
        action['domain'] = [('group_id', 'in', self.mapped('group_id').ids)]
        return action

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    @api.multi
    def cancel(self):
        to_cancel = self.filtered(lambda procurement: procurement.state != 'done')
        if to_cancel:
            return to_cancel.write({'state': 'cancel'})

    @api.multi
    def reset_to_confirmed(self):
        return self.write({'state': 'confirmed'})

    @api.multi
    def run(self, autocommit=False):
        # TDE FIXME: avoid browsing everything -> avoid prefetching ?
        for procurement in self:
            # we intentionnaly do the browse under the for loop to avoid caching all ids which would be resource greedy
            # and useless as we'll make a refresh later that will invalidate all the cache (and thus the next iteration
            # will fetch all the ids again)
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
                        self.env.cr.commit()
                except OperationalError:
                    if autocommit:
                        self.env.cr.rollback()
                        continue
                    else:
                        raise
        return True

    @api.multi
    @api.returns('self', lambda procurements: [procurement.id for procurement in procurements])
    def check(self, autocommit=False):
        # TDE FIXME: check should not do something, just check
        procurements_done = self.env['procurement.order']
        for procurement in self:
            try:
                result = procurement._check()
                if result:
                    procurements_done += procurement
                if autocommit:
                    self.env.cr.commit()
            except OperationalError:
                if autocommit:
                    self.env.cr.rollback()
                    continue
                else:
                    raise
        if procurements_done:
            procurements_done.write({'state': 'done'})
        return procurements_done

    #
    # Method to overwrite in different procurement modules
    #
    @api.multi
    def _find_suitable_rule(self):
        '''This method returns a procurement.rule that depicts what to do with the given procurement
        in order to complete its needs. It returns False if no suiting rule is found.
            :rtype: int or False
        '''
        return False

    @api.multi
    def _assign(self):
        '''This method check what to do with the given procurement in order to complete its needs.
        It returns False if no solution is found, otherwise it stores the matching rule (if any) and
        returns True.
            :rtype: boolean
        '''
        # if the procurement already has a rule assigned, we keep it (it has a higher priority as it may have been chosen manually)
        if self.rule_id:
            return True
        elif self.product_id.type not in ('service', 'digital'):
            rule = self._find_suitable_rule()
            if rule:
                self.write({'rule_id': rule.id})
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
            :rtype: boolean
        '''
        return False

    #
    # Scheduler
    #
    @api.model
    def run_scheduler(self, use_new_cursor=False, company_id=False):
        '''
        Call the scheduler to check the procurement order. This is intented to be done for all existing companies at
        the same time, so we're running all the methods as SUPERUSER to avoid intercompany and access rights issues.

        @param use_new_cursor: if set, use a dedicated cursor and auto-commit after processing each procurement.
            This is appropriate for batch jobs only.
        @return:  Dictionary of values
        '''
        ProcurementSudo = self.env['procurement.order'].sudo()
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME

            # Run confirmed procurements
            procurements = ProcurementSudo.search([('state', '=', 'confirmed')] + (company_id and [('company_id', '=', company_id)] or []))
            while procurements:
                procurements.run(autocommit=use_new_cursor)
                if use_new_cursor:
                    self.env.cr.commit()
                procurements = ProcurementSudo.search([('id', 'not in', procurements.ids), ('state', '=', 'confirmed')] + (company_id and [('company_id', '=', company_id)] or []))

            # Check done procurements
            procurements = ProcurementSudo.search([('state', '=', 'running')] + (company_id and [('company_id', '=', company_id)] or []))
            while procurements:
                procurements.check(autocommit=use_new_cursor)
                if use_new_cursor:
                    self.env.cr.commit()
                procurements = ProcurementSudo.search([('id', 'not in', procurements.ids), ('state', '=', 'running')] + (company_id and [('company_id', '=', company_id)] or []))

        finally:
            if use_new_cursor:
                try:
                    self.env.cr.close()
                except Exception:
                    pass
        return {}
