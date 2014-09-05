# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today OpenERP SA (<http://www.openerp.com>)
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

from openerp import tools
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _


class invite_wizard(osv.osv_memory):
    """ Wizard to invite partners and make them followers. """
    _name = 'mail.wizard.invite'
    _description = 'Invite wizard'

    def default_get(self, cr, uid, fields, context=None):
        result = super(invite_wizard, self).default_get(cr, uid, fields, context=context)
        user_name = self.pool.get('res.users').name_get(cr, uid, [uid], context=context)[0][1]
        model = result.get('res_model')
        res_id = result.get('res_id')
        if 'message' in fields and model and res_id:
            ir_model = self.pool.get('ir.model')
            model_ids = ir_model.search(cr, uid, [('model', '=', self.pool[model]._name)], context=context)
            model_name = ir_model.name_get(cr, uid, model_ids, context=context)[0][1]

            document_name = self.pool[model].name_get(cr, uid, [res_id], context=context)[0][1]
            message = _('<div><p>Hello,</p><p>%s invited you to follow %s document: %s.<p></div>') % (user_name, model_name, document_name)
            result['message'] = message
        elif 'message' in fields:
            result['message'] = _('<div><p>Hello,</p><p>%s invited you to follow a new document.</p></div>') % user_name
        return result

    _columns = {
        'res_model': fields.char('Related Document Model',
                        required=True, select=1,
                        help='Model of the followed resource'),
        'res_id': fields.integer('Related Document ID', select=1,
                        help='Id of the followed resource'),
        'partner_ids': fields.many2many('res.partner', string='Recipients',
            help="List of partners that will be added as follower of the current document."),
        'message': fields.html('Message'),
        'send_mail': fields.boolean('Send Email',
            help="If checked, the partners will receive an email warning they have been "
                    "added in the document's followers."),
    }
    
    _defaults = {
        'send_mail' : True,
    }

    def add_followers(self, cr, uid, ids, context=None):
        for wizard in self.browse(cr, uid, ids, context=context):
            model_obj = self.pool[wizard.res_model]
            document = model_obj.browse(cr, uid, wizard.res_id, context=context)

            # filter partner_ids to get the new followers, to avoid sending email to already following partners
            new_follower_ids = [p.id for p in wizard.partner_ids if p not in document.message_follower_ids]
            model_obj.message_subscribe(cr, uid, [wizard.res_id], new_follower_ids, context=context)

            ir_model = self.pool.get('ir.model')
            model_ids = ir_model.search(cr, uid, [('model', '=', model_obj._name)], context=context)
            model_name = ir_model.name_get(cr, uid, model_ids, context=context)[0][1]

            # send an email if option checked and if a message exists (do not send void emails)
            if wizard.send_mail and wizard.message and not wizard.message == '<br>':  # when deleting the message, cleditor keeps a <br>
                # add signature
                # FIXME 8.0: use notification_email_send, send a wall message and let mail handle email notification + message box
                signature_company = self.pool.get('mail.notification').get_signature_footer(cr, uid, user_id=uid, res_model=wizard.res_model, res_id=wizard.res_id, context=context)
                wizard.message = tools.append_content_to_html(wizard.message, signature_company, plaintext=False, container_tag='div')

                # send mail to new followers
                # the invite wizard should create a private message not related to any object -> no model, no res_id
                mail_mail = self.pool.get('mail.mail')
                mail_id = mail_mail.create(cr, uid, {
                    'model': wizard.res_model,
                    'res_id': wizard.res_id,
                    'subject': _('Invitation to follow %s: %s') % (model_name, document.name_get()[0][1]),
                    'body_html': '%s' % wizard.message,
                    'auto_delete': True,
                    'recipient_ids': [(4, id) for id in new_follower_ids]
                    }, context=context)
                mail_mail.send(cr, uid, [mail_id], context=context)
        return {'type': 'ir.actions.act_window_close'}
