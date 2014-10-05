# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _


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

    def button_confirm(self, cr, uid, ids, context=None):
        '''
        create registration with sales order
        '''
        context = dict(context or {})
        registration_obj = self.pool.get('event.registration')
        for order_line in self.browse(cr, uid, ids, context=context):
            if order_line.event_id:
                dic = {
                    'name': order_line.order_id.partner_invoice_id.name,
                    'partner_id': order_line.order_id.partner_id.id,
                    'nb_register': int(order_line.product_uom_qty),
                    'email': order_line.order_id.partner_id.email,
                    'phone': order_line.order_id.partner_id.phone,
                    'origin': order_line.order_id.name,
                    'event_id': order_line.event_id.id,
                    'event_ticket_id': order_line.event_ticket_id and order_line.event_ticket_id.id or None,
                }

                if order_line.event_ticket_id:
                    message = _("The registration has been created for event <i>%s</i> with the ticket <i>%s</i> from the Sale Order %s. ") % (order_line.event_id.name, order_line.event_ticket_id.name, order_line.order_id.name)
                else:
                    message = _("The registration has been created for event <i>%s</i> from the Sale Order %s. ") % (order_line.event_id.name, order_line.order_id.name)

                context.update({'mail_create_nolog': True})
                registration_id = registration_obj.create(cr, uid, dic, context=context)
                registration_obj.message_post(cr, uid, [registration_id], body=message, context=context)
        return super(sale_order_line, self).button_confirm(cr, uid, ids, context=context)

    def onchange_event_ticket_id(self, cr, uid, ids, event_ticket_id=False, context=None):
        price = event_ticket_id and self.pool["event.event.ticket"].browse(cr, uid, event_ticket_id, context=context).price or False
        return {'value': {'price_unit': price}}
