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


class crm_lead_forward_to_partner(osv.TransientModel):
    """ Forward info history to partners. """
    _name = 'crm.lead.forward.to.partner'
    _inherit = "mail.compose.message"

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
        'history_mode': fields.selection([('info', 'Internal notes'),
            ('latest', 'Latest email'), ('whole', 'Whole Story')],
            'Send history', required=True),
    }

    _defaults = {
        'history_mode': 'info',
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        # set as comment, perform overrided document-like action that calls get_record_data
        old_mode = context.get('default_composition_mode', 'forward')
        context['default_composition_mode'] = 'comment'
        res = super(crm_lead_forward_to_partner, self).default_get(cr, uid, fields, context=context)
        # back to forward mode
        context['default_composition_mode'] = old_mode
        res['composition_mode'] = context['default_composition_mode']
        return res

    def get_record_data(self, cr, uid, model, res_id, context=None):
        """ Override of mail.compose.message, to add default values coming
            form the related lead.
        """
        if context is None:
            context = {}
        res = super(crm_lead_forward_to_partner, self).get_record_data(cr, uid, model, res_id, context=context)
        if model not in ('crm.lead') or not res_id:
            return res
        template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', 'crm_partner_assign_email_template')[1]
        context['history_mode'] = context.get('history_mode','whole')
        mail_body_fields = ['partner_id', 'partner_name', 'title', 'function', 'street', 'street2', 'zip', 'city', 'country_id', 'state_id', 'email_from', 'phone', 'fax', 'mobile', 'description']
        lead = self.pool.get('crm.lead').browse(cr, uid, res_id, context=context)
        context['mail_body'] = self.pool.get('crm.lead')._mail_body(cr, uid, lead, mail_body_fields, context=context)
        template = self.generate_email_for_composer(cr, uid, template_id, res_id, context)
        res['subject'] = template['subject']
        res['body'] = template['body']
        return res

    def on_change_history_mode(self, cr, uid, ids, history_mode, model, res_id, context=None):
        """ Update body when changing history_mode """
        if context is None:
            context = {}
        if model and model == 'crm.lead' and res_id:
            lead = self.pool.get(model).browse(cr, uid, res_id, context=context)
            context['history_mode'] = history_mode
            body = self.get_record_data(cr, uid, 'crm.lead', res_id, context=context)['body']
            return {'value': {'body': body}}

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
        """ Forward the lead to a partner """
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

        return self.send_mail(cr, uid, ids, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
