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

import re
import time
import tools

from osv import osv, fields
from tools.translate import _

class crm_lead_forward_to_partner(osv.osv_memory):
    """ Forward info history to partners. """
    _name = 'crm.lead.forward.to.partner'
    _inherit = "mail.compose.message"

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        # set as comment, perform overrided document-like action that calls get_record_data
        old_mode = context.get('mail.compose.message.mode', 'forward')
        context['mail.compose.message.mode'] = 'comment'
        res = super(crm_lead_forward_to_partner, self).default_get(cr, uid, fields, context=context)
        # back to forward mode
        context['mail.compose.message.mode'] = old_mode
        res['composition_mode'] = context['mail.compose.message.mode']
        return res

    def _get_composition_mode_selection(self, cr, uid, context=None):
        composition_mode = super(crm_lead_forward_to_partner, self)._get_composition_mode_selection(cr, uid, context=context)
        composition_mode.append(('forward', 'Forward'))
        return composition_mode

    _columns = {
        'partner_ids': fields.many2many('res.partner',
            'lead_forward_to_partner_res_partner_rel',
            'wizard_id', 'partner_id', 'Additional contacts'),
        'attachment_ids': fields.many2many('ir.attachment',
            'lead_forward_to_partner_attachment_rel',
            'wizard_id', 'attachment_id', 'Attachments'),
        'history_mode': fields.selection([('info', 'Case Information'),
            ('latest', 'Latest email'), ('whole', 'Whole Story')],
            'Send history', required=True),
    }

    _defaults = {
        'history_mode': 'latest',
        'content_subtype': lambda self,cr, uid, context={}: 'html',
    }

    def get_record_data(self, cr, uid, model, res_id, context=None):
        """ Override of mail.compose.message, to add default values coming
            form the related lead.
        """
        res = super(crm_lead_forward_to_partner, self).get_record_data(cr, uid, model, res_id, context=context)
        if model not in ('crm.lead') or not res_id:
            return res
        lead_obj = self.pool.get(model)
        lead = lead_obj.browse(cr, uid, res_id, context=context)
        subject = '%s: %s - %s' % (_('Fwd'), _('Lead forward'), lead.name)
        body = self._get_message_body(cr, uid, lead, 'info', context=context)
        res.update({
            'subject': subject,
            'body': body,
            })
        return res

    def on_change_history_mode(self, cr, uid, ids, history_mode, model, res_id, context=None):
        """ Update body when changing history_mode """
        if model and model == 'crm.lead' and res_id:
            lead = self.pool.get(model).browse(cr, uid, res_id, context=context)
            body = self._get_message_body(cr, uid, lead, history_mode, context=context)
            return {'value': {'body': body}}
    
    def on_change_partner_ids(self, cr, uid, ids, partner_ids, context=None):
        """ TDE-TODO: Keep void; maybe we could check that partner_ids have
            email  defined. """
        return {}

    def create(self, cr, uid, values, context=None):
        """ TDE-HACK: remove 'type' from context, because when viewing an
            opportunity form view, a default_type is set and propagated
            to the wizard, that has a not matching type field. """
        default_type = context.pop('default_type', None)
        new_id = super(crm_lead_forward_to_partner, self).create(cr, uid, values, context=context)
        if default_type:
            context['default_type'] = default_type
        return new_id

    def action_forward(self, cr, uid, ids, context=None):
        """
            Forward the lead to a partner
        """
        if context is None:
            context = {}
        res = {'type': 'ir.actions.act_window_close'}
        wizard = self.browse(cr, uid, ids[0], context=context)
        if wizard.model not in ('crm.lead'):
            return res

        lead = self.pool.get(wizard.model)
        lead_ids = wizard.res_id and [wizard.res_id] or []

        if wizard.composition_mode == 'mass_mail':
            lead_ids = context and context.get('active_ids', []) or []
            value = self.default_get(cr, uid, ['body', 'email_to', 'email_cc', 'subject', 'history_mode'], context=context)
            self.write(cr, uid, ids, value, context=context)

        self.send_mail(cr, uid, ids, context=context)
        # for case in lead.browse(cr, uid, lead_ids, context=context):
            # TDE: WHAT TO DO WITH THAT ?
            # if (this.send_to == 'partner' and this.partner_id):
            #     lead.assign_partner(cr, uid, [case.id], this.partner_id.id, context=context)

            # if this.send_to == 'user':
            #     lead.allocate_salesman(cr, uid, [case.id], [this.user_id.id], context=context)
        return res

    def _get_info_body(self, cr, uid, lead, context=None):
        field_names = []
        proxy = self.pool.get(lead._name)
        if lead.type == 'opportunity':
            field_names += ['partner_id']
        field_names += [
            'partner_name' , 'title', 'function', 'street', 'street2',
            'zip', 'city', 'country_id', 'state_id', 'email_from',
            'phone', 'fax', 'mobile', 'categ_id', 'description',
        ]
        return proxy._mail_body(cr, uid, lead, field_names, context=context)

    def _get_message_body(self, cr, uid, lead, history_mode='whole', context=None):
        """ This function gets whole communication history and returns as top
            posting style
            #1: form a body, based on the lead
            #2: append to the body the communication history, based on the
                history_mode parameter

            - info: Forward the case information
            - latest: Send the latest history
            - whole: Send the whole history

            :param lead: browse_record on crm.lead
            :param history_mode: 'whole' or 'latest'
        """
        mail_message = self.pool.get('mail.message')
        body = self._get_info_body(cr, uid, lead, context=context)
        if history_mode not in ('whole', 'latest'):
            return body or ''
        for message in lead.message_ids:
            header = '-------- Original Message --------'
            sentdate = 'Date: %s' % (message.date or '')
            desc = '\n%s'%(message.body)
            original = [header, sentdate, desc, '\n']
            original = '\n'.join(original)
            body += original
            if history_mode == 'latest':
                break
        return body or ''


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
