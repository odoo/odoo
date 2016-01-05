# -*- coding: utf-8 -*-

from openerp import api
from openerp.osv import fields, osv


class sale_order(osv.osv):
    _inherit = "sale.order"

    def action_confirm(self, cr, uid, ids, context=None):
        res = super(sale_order, self).action_confirm(cr, uid, ids, context=context)
        for order in self.browse(cr, uid, ids, context=context):
            redirect_to_event_registration, so_id = any(line.event_id for line in order.order_line), order.id
            order.order_line._update_registrations(confirm=True)
        if redirect_to_event_registration:
            event_ctx = dict(context, default_sale_order_id=so_id)
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
        'event_type_id': fields.related('product_id', 'event_type_id', type='many2one', relation="event.type", string="Event Type", readonly=True),
        'event_ok': fields.related('product_id', 'event_ok', string='event_ok', type='boolean', readonly=True),
    }

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
        if line.event_id:
            event = self.pool['event.event'].read(cr, uid, line.event_id.id, ['name'], context=context)
            res['name'] = '%s: %s' % (res.get('name', ''), event['name'])
        return res

    @api.onchange('product_id')
    def product_id_change_event(self):
        if self.product_id.event_ok:
            values = dict(event_type_id=self.product_id.event_type_id.id,
                          event_ok=self.product_id.event_ok)
        else:
            values = dict(event_type_id=False, event_ok=False)
        self.update(values)

    @api.multi
    def _update_registrations(self, confirm=True, registration_data=None):
        """ Create or update registrations linked to a sale order line. A sale
        order line has a product_uom_qty attribute that will be the number of
        registrations linked to this line. This method update existing registrations
        and create new one for missing one. """
        Registration = self.env['event.registration']
        registrations = Registration.search([('sale_order_line_id', 'in', self.ids)])
        for so_line in [l for l in self if l.event_id]:
            existing_registrations = registrations.filtered(lambda self: self.sale_order_line_id.id == so_line.id)
            if confirm:
                existing_registrations.filtered(lambda self: self.state != 'open').confirm_registration()
            else:
                existing_registrations.filtered(lambda self: self.state == 'cancel').do_draft()

            for count in range(int(so_line.product_uom_qty) - len(existing_registrations)):
                registration = {}
                if registration_data:
                    registration = registration_data.pop()
                # TDE CHECK: auto confirmation
                registration['sale_order_line_id'] = so_line
                self.env['event.registration'].with_context(registration_force_draft=True).create(
                    Registration._prepare_attendee_values(registration))
        return True

    def onchange_event_ticket_id(self, cr, uid, ids, event_ticket_id=False, context=None):
        price = event_ticket_id and self.pool["event.event.ticket"].browse(cr, uid, event_ticket_id, context=context).price or False
        return {'value': {'price_unit': price}}
