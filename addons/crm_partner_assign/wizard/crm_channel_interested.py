# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError


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
            raise UserError(_("You must contact the lead before saying that you are interested"))
        lead_obj = self.pool.get('crm.lead')
        lead_obj.check_access_rights(cr, uid, 'write')
        if wizard.interested:
            message = _('<p>I am interested by this lead.</p>')
            values = {}
        else:
            stage = 'stage_portal_lead_recycle'
            if wizard.contacted:
                message = _('<p>I am not interested by this lead. I contacted the lead.</p>')
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
