# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from tools.translate import _
from decimal_precision import decimal_precision as dp

class partner_event_registration(osv.osv_memory):
    """  event Registration """

    _name = "partner.event.registration"
    _description = __doc__
    _order = 'event_id'

    _columns = {
        'event_id': fields.many2one('event.event', 'Event'),
        'event_type': fields.many2one('event.type', 'Type', readonly=True),
        'unit_price': fields.float('Registration Cost', digits_compute=dp.get_precision('Sale Price')),
        'start_date': fields.datetime('Start date', required=True, help="Beginning Date of Event", readonly=True),
        'end_date': fields.datetime('Closing date', required=True, help="Closing Date of Event", readonly=True),
        'nb_register': fields.integer('Number of Registration'),
    }
    _defaults = {
        'nb_register': 1,
    }

    def open_registration(self, cr, uid, ids, context=None):
        """This Function Open Registration For Given Event id and Partner.

        """
        value = {}
        res_obj = self.pool.get('res.partner')
        job_obj = self.pool.get('res.partner.job')
        reg_obj = self.pool.get('event.registration')
        mod_obj = self.pool.get('ir.model.data')

        record_ids = context and context.get('active_ids', []) or []
        addr = res_obj.address_get(cr, uid, record_ids)
        contact_id = False
        email = False
        if addr.has_key('default'):
                job_ids = job_obj.search(cr, uid, [('address_id', '=', addr['default'])], context=context)
                if job_ids:
                    contact = job_obj.browse(cr, uid, job_ids[0], context=context)
                    if contact:
                        contact_id = contact.contact_id.id
                        email = contact.email

        result = mod_obj.get_object_reference(cr, uid, 'event', 'view_registration_search')
        res = result and result[1] or False

        # Select the view

        id2 = mod_obj.get_object_reference(cr, uid, 'event', 'view_event_registration_form')
        id2 = id2 and id2[1] or False
        id3 = mod_obj.get_object_reference(cr, uid, 'event', 'view_event_registration_tree')
        id3 = id3 and id3[1] or False

        for current in self.browse(cr, uid, ids, context=context):
            for partner in res_obj.browse(cr, uid, record_ids, context=context):
                new_case = reg_obj.create(cr, uid, {
                        'name': 'Registration',
                        'event_id': current.event_id and current.event_id.id or False,
                        'unit_price': current.unit_price,
                        'partner_id': partner.id,
                        'partner_invoice_id':  partner.id,
                        'event_product': current.event_id.product_id.name,
                        'contact_id': contact_id,
                        'email_from': email,
                        'nb_register': current.nb_register,

                }, context=context)

        value = {
                'name': _('Event Registration'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'event.registration',
                'res_id': new_case,
                'views': [(id2, 'form'), (id3, 'tree'), (False, 'calendar'), (False, 'graph')],
                'type': 'ir.actions.act_window',
                'search_view_id': res
        }
        return value

    def name_get(self, cr, uid, ids, context=None):
        """Overrides orm name_get method
        @param ids: List of partner_event_register ids
        """
        if not context:
            context = {}

        res = []
        if not ids:
            return res
        reads = self.read(cr, uid, ids, ['event_type', 'event_id'], context=context)
        for record in reads:
            event_id = record['event_id'][1]
            if record['event_type']:
                event_id = record['event_type'][1] + ' on ' + event_id
            res.append((record['id'], event_id))
        return res

    def onchange_event_id(self, cr, uid, ids, event_id, context=None):
        res = {}
        event_obj = self.pool.get('event.event')
        product_obj = self.pool.get('product.product')
        partner_obj = self.pool.get('res.partner')
        if not context:
            context = {}
        partner_id = context.get('active_id', False)
        if event_id:
            event = event_obj.browse(cr, uid, event_id, context=context)
            pricelist_id = event.pricelist_id and event.pricelist_id.id or False
            if partner_id:
                partner = partner_obj.browse(cr, uid, partner_id, context=context)
                pricelist_id = pricelist_id or partner.property_product_pricelist.id
            unit_price = product_obj._product_price(cr, uid, [event.product_id.id], False, False, {'pricelist': pricelist_id})[event.product_id.id]

            res['value'] = {
                          'event_type': event.type and event.type.id or False,
                          'start_date': event.date_begin,
                          'end_date': event.date_end,
                          'unit_price': unit_price,
            }
        return res

partner_event_registration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: