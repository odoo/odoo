# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2010-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv, fields
from tools.translate import _
from email_template.email_template import get_value


class email_template_preview(osv.osv_memory):
    _name = "email_template.preview"
    _description = "Email Template Preview"

    def _get_model_recs(self, cr, uid, context=None):
        if context is None:
            context = {}
            #Fills up the selection box which allows records from the selected object to be displayed
        self.context = context
        if 'template_id' in context:
            ref_obj_id = self.pool.get('email.template').read(cr, uid, context['template_id'], ['object_name'], context)
            ref_obj_name = self.pool.get('ir.model').read(cr, uid, ref_obj_id['object_name'][0], ['model'], context)['model']
            model_obj = self.pool.get(ref_obj_name)
            ref_obj_ids = model_obj.search(cr, uid, [], 0, 20, 'id', context=context)
            if not ref_obj_ids:
                ref_obj_ids = []

            # also add the default one if requested, otherwise it won't be available for selection:
            default_id = context.get('default_rel_model_ref')
            if default_id and default_id not in ref_obj_ids:
                ref_obj_ids.insert(0, default_id)
            return model_obj.name_get(cr, uid, ref_obj_ids, context)
        return []

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_template_preview, self).default_get(cr, uid, fields, context=context)
        if (not fields or 'rel_model_ref' in fields) and 'template_id' in context \
           and not result.get('rel_model_ref'):
            selectables = self._get_model_recs(cr, uid, context=context)
            result['rel_model_ref'] = selectables and selectables[0][0] or False
        return result

    def _default_model(self, cursor, user, context=None):
        """
        Returns the default value for model field
        @param cursor: Database Cursor
        @param user: ID of current user
        @param context: OpenERP Context
        """
        return self.pool.get('email.template').read(
                                                   cursor,
                                                   user,
                                                   context['template_id'],
                                                   ['object_name'],
                                                   context).get('object_name', False)

    _columns = {
        'ref_template':fields.many2one(
                                       'email.template',
                                       'Template', readonly=True),
        'rel_model':fields.many2one('ir.model', 'Model', readonly=True),
        'rel_model_ref':fields.selection(_get_model_recs, 'Referred Document'),
        'to':fields.char('To', size=250, readonly=True),
        'cc':fields.char('CC', size=250, readonly=True),
        'bcc':fields.char('BCC', size=250, readonly=True),
        'reply_to':fields.char('Reply-To',
                    size=250,
                    help="The address recipients should reply to,"
                         " if different from the From address."
                         " Placeholders can be used here."),
        'message_id':fields.char('Message-ID',
                    size=250,
                    help="The Message-ID header value, if you need to"
                         "specify it, for example to automatically recognize the replies later."
                        " Placeholders can be used here."),
        'subject':fields.char('Subject', size=200, readonly=True),
        'body_text':fields.text('Body', readonly=True),
        'body_html':fields.text('Body', readonly=True),
        'report':fields.char('Report Name', size=100, readonly=True),
    }
    _defaults = {
        'ref_template': lambda self, cr, uid, ctx:ctx['template_id'] or False,
        'rel_model': _default_model,
    }
    def on_change_ref(self, cr, uid, ids, rel_model_ref, context=None):
        if context is None:
            context = {}
        if not rel_model_ref:
            return {}
        vals = {}
        if context == {}:
            context = self.context
        template = self.pool.get('email.template').browse(cr, uid, context['template_id'], context)
        #Search translated template
        lang = get_value(cr, uid, rel_model_ref, template.lang, template, context)
        if lang:
            ctx = context.copy()
            ctx.update({'lang':lang})
            template = self.pool.get('email.template').browse(cr, uid, context['template_id'], ctx)
        vals['to'] = get_value(cr, uid, rel_model_ref, template.def_to, template, context)
        vals['cc'] = get_value(cr, uid, rel_model_ref, template.def_cc, template, context)
        vals['bcc'] = get_value(cr, uid, rel_model_ref, template.def_bcc, template, context)
        vals['reply_to'] = get_value(cr, uid, rel_model_ref, template.reply_to, template, context)
        if template.message_id:
            vals['message_id'] = get_value(cr, uid, rel_model_ref, template.message_id, template, context)
        elif template.track_campaign_item:
            vals['message_id'] = tools.misc.generate_tracking_message_id(rel_model_ref)
        vals['subject'] = get_value(cr, uid, rel_model_ref, template.def_subject, template, context)
        vals['body_text'] = get_value(cr, uid, rel_model_ref, template.def_body_text, template, context)
        vals['body_html'] = get_value(cr, uid, rel_model_ref, template.def_body_html, template, context)
        vals['report'] = get_value(cr, uid, rel_model_ref, template.file_name, template, context)
        return {'value':vals}

email_template_preview()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
