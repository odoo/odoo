# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID


class crm_lead_forward_to_partner(osv.TransientModel):
    """ Forward info history to partners. """
    _name = 'crm.lead.channel.interested'
    _columns = {
        'interested': fields.boolean('Interested by this lead'),
        'contacted': fields.boolean('Did you contact the lead?', help="The lead has been contacted"),
        'comment': fields.text('Comment', help="What are the elements that have led to this decision?", required=True),
    }
    _defaults = {
        'interested': lambda self, cr, uid, c: c.get('interested', True),
        'contacted': False,
    }

    def action_confirm(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        if wizard.interested and not wizard.contacted:
            raise osv.except_osv(_('Error!'), _("You must contact the lead before saying that you are interested"))
        lead_obj = self.pool.get('crm.lead')
        lead_obj.check_access_rights(cr, uid, 'write')
        if wizard.interested:
            message = _('<p>I am interested by this lead.</p>')
            values = {}
        else:
            stage = 'stage_portal_lead_recycle'
            if wizard.contacted:
                message = _('<p>I am not interested by this lead. I %scontacted the lead.</p>') % ''
            else:
                message = _('<p>I am not interested by this lead. I have not contacted the lead.</p>')
            values = {'partner_assigned_id': False}
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            partner_ids = self.pool.get('res.partner').search(cr, SUPERUSER_ID, [('id', 'child_of', user.partner_id.commercial_partner_id.id)], context=context)
            lead_obj.message_unsubscribe(cr, SUPERUSER_ID, context.get('active_ids', []), partner_ids, context=None)
            try:
                stage_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', stage)[1]
            except ValueError:
                stage_id = False
            if stage_id:
                values.update({'stage_id': stage_id})
        if wizard.comment:
            message += '<p>%s</p>' % wizard.comment
        for active_id in context.get('active_ids', []):
            lead_obj.message_post(cr, uid, active_id, body=message, subtype="mail.mt_comment", context=context)
        if values:
            lead_obj.write(cr, SUPERUSER_ID, context.get('active_ids', []), values)
        if wizard.interested:
            for lead in lead_obj.browse(cr, uid, context.get('active_ids', []), context=context):
                lead_obj.convert_opportunity(cr, SUPERUSER_ID, [lead.id], lead.partner_id and lead.partner_id.id or None, context=None)
        return {
            'type': 'ir.actions.act_window_close',
        }
