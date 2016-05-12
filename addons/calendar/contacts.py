# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import fields, osv


class calendar_contacts(osv.osv):
    _name = 'calendar.contacts'

    _columns = {
        'user_id': fields.many2one('res.users', 'Me'),
        'partner_id': fields.many2one('res.partner', 'Employee', required=True, domain=[]),
        'active': fields.boolean('active'),
    }

    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'active': True,
    }

    def unlink_from_partner_id(self, cr, uid, partner_id, context=None):
        self.unlink(cr, uid, self.search(cr, uid, [('partner_id', '=', partner_id)]), context)
