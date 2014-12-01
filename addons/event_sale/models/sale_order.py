# -*- coding: utf-8 -*-

from openerp import api
from openerp.osv import fields, osv


class sale_order(osv.osv):
    _inherit = "sale.order"

    def action_button_confirm(self, cr, uid, ids, context=None):
        # TDE note: This method works on a list of one id (see sale/sale.py) so working on ids[0] seems safe.
        res = super(sale_order, self).action_button_confirm(cr, uid, ids, context=context)
        redirect_to_event_registration = any(line.event_id for order in self.browse(cr, uid, ids, context=context) for line in order.order_line)
        if redirect_to_event_registration:
            event_ctx = dict(context, default_sale_order_id=ids[0])
            return self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'event_sale', 'action_sale_order_event_registration', event_ctx)
        else:
            return res


class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _columns = {
        'event_id': fields.many2one(
            'event.event', 'Event',
            help="Choose an event and it will automatically create a registration for this event."),
        'event_ticket_id': fields.many2one(
            'event.event.ticket', 'Event Ticket',
            help="Choose an event ticket and it will automatically create a registration for this event ticket."),
        # those 2 fields are used for dynamic domains and filled by onchange
        # TDE: really necessary ? ...
        'event_type_id': fields.related('product_id', 'event_type_id', type='many2one', relation="event.type", string="Event Type"),
        'event_ok': fields.related('product_id', 'event_ok', string='event_ok', type='boolean'),
    }

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
        if line.event_id:
            event = self.pool['event.event'].read(cr, uid, line.event_id.id, ['name'], context=context)
            res['name'] = '%s: %s' % (res.get('name', ''), event['name'])
        return res

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0, uom=False,
                          qty_uos=0, uos=False, name='', partner_id=False, lang=False,
                          update_tax=True, date_order=False, packaging=False,
                          fiscal_position=False, flag=False, context=None):
        """ check product if event type """
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id, lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        if product:
            product_res = self.pool.get('product.product').browse(cr, uid, product, context=context)
            if product_res.event_ok:
                res['value'].update(event_type_id=product_res.event_type_id.id,
                                    event_ok=product_res.event_ok)
            else:
                res['value'].update(event_type_id=False,
                                    event_ok=False)
        return res

    @api.multi
    def _update_registrations(self):
        """ Create or update registrations linked to a sale order line. A sale
        order line has a product_uom_qty attribute that will be the number of
        registrations linked to this line. This method update existing registrations
        and create new one for missing one. """
        registrations = self.env['event.registration'].search([('origin', 'in', list(set([so.name for line in self for so in line.order_id if line.event_id])))])
        for so_line in [l for l in self if l.event_id]:
            existing_registrations = [r for r in registrations if r.event_id == so_line.event_id and r.origin == so_line.order_id.name]
            for registration in existing_registrations:
                registration.write({'state': 'open'})

            for count in range(int(so_line.product_uom_qty) - len(existing_registrations)):
                self.env['event.registration'].create({
                    'event_id': so_line.event_id.id,
                    'event_ticket_id': so_line.event_ticket_id.id,
                    'partner_id': so_line.order_id.partner_id.id,
                    'origin': so_line.order_id.name,
                })
        return True

    def button_confirm(self, cr, uid, ids, context=None):
        """ Override confirmation of the sale order line in order to create
        or update the possible event registrations linked to the sale. """
        '''
        create registration with sales order
        '''
        res = super(sale_order_line, self).button_confirm(cr, uid, ids, context=context)
        self._update_registrations(cr, uid, ids, context=context)
        return res

    def onchange_event_ticket_id(self, cr, uid, ids, event_ticket_id=False, context=None):
        price = event_ticket_id and self.pool["event.event.ticket"].browse(cr, uid, event_ticket_id, context=context).price or False
        return {'value': {'price_unit': price}}
