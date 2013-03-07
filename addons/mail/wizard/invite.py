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
        if 'message' in fields and result.get('res_model') and result.get('res_id'):
            document_name = self.pool.get(result.get('res_model')).name_get(cr, uid, [result.get('res_id')], context=context)[0][1]
            message = _('<div>You have been invited to follow %s.</div>' % document_name)
            result['message'] = message
        elif 'message' in fields:
            result['message'] = _('<div>You have been invited to follow a new document.</div>')
        return result

    _columns = {
        'res_model': fields.char('Related Document Model', size=128,
                        required=True, select=1,
                        help='Model of the followed resource'),
        'res_id': fields.integer('Related Document ID', select=1,
                        help='Id of the followed resource'),
        'partner_ids': fields.many2many('res.partner', string='Partners'),
        'message': fields.html('Message'),
    }

    def add_followers(self, cr, uid, ids, context=None):
        for wizard in self.browse(cr, uid, ids, context=context):
            model_obj = self.pool.get(wizard.res_model)
            document = model_obj.browse(cr, uid, wizard.res_id, context=context)

            # filter partner_ids to get the new followers, to avoid sending email to already following partners
            new_follower_ids = [p.id for p in wizard.partner_ids if p.id not in document.message_follower_ids]
            model_obj.message_subscribe(cr, uid, [wizard.res_id], new_follower_ids, context=context)

            # send an email
            if wizard.message:
                # add signature
                user_id = self.pool.get("res.users").read(cr, uid, [uid], fields=["signature"], context=context)[0]
                signature = user_id and user_id["signature"] or ''
                if signature:
                    wizard.message = tools.append_content_to_html(wizard.message, signature, plaintext=True, container_tag='div')
                # FIXME 8.0: use notification_email_send, send a wall message and let mail handle email notification + message box
                for follower_id in new_follower_ids:
                    mail_mail = self.pool.get('mail.mail')
                    # the invite wizard should create a private message not related to any object -> no model, no res_id
                    mail_id = mail_mail.create(cr, uid, {
                        'model': wizard.res_model,
                        'res_id': wizard.res_id,
                        'subject': 'Invitation to follow %s' % document.name_get()[0][1],
                        'body_html': '%s' % wizard.message,
                        'auto_delete': True,
                        }, context=context)
                    mail_mail.send(cr, uid, [mail_id], recipient_ids=[follower_id], context=context)
        return {'type': 'ir.actions.act_window_close'}
