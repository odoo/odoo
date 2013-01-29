# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
from openerp.osv import osv, fields
from openerp import tools, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.tools.mail import plaintext2html

class mail_followers(osv.Model):
    """ mail_followers holds the data related to the follow mechanism inside
        OpenERP. Partners can choose to follow documents (records) of any kind
        that inherits from mail.thread. Following documents allow to receive
        notifications for new messages.
        A subscription is characterized by:
            :param: res_model: model of the followed objects
            :param: res_id: ID of resource (may be 0 for every objects)
    """
    _name = 'mail.followers'
    _rec_name = 'partner_id'
    _log_access = False
    _description = 'Document Followers'
    _columns = {
        'res_model': fields.char('Related Document Model', size=128,
                        required=True, select=1,
                        help='Model of the followed resource'),
        'res_id': fields.integer('Related Document ID', select=1,
                        help='Id of the followed resource'),
        'partner_id': fields.many2one('res.partner', string='Related Partner',
                        ondelete='cascade', required=True, select=1),
        'subtype_ids': fields.many2many('mail.message.subtype', string='Subtype',
            help="Message subtypes followed, meaning subtypes that will be pushed onto the user's Wall."),
    }


class mail_notification(osv.Model):
    """ Class holding notifications pushed to partners. Followers and partners
        added in 'contacts to notify' receive notifications. """
    _name = 'mail.notification'
    _rec_name = 'partner_id'
    _log_access = False
    _description = 'Notifications'

    _columns = {
        'partner_id': fields.many2one('res.partner', string='Contact',
                        ondelete='cascade', required=True, select=1),
        'read': fields.boolean('Read', select=1),
        'starred': fields.boolean('Starred', select=1,
            help='Starred message that goes into the todo mailbox'),
        'message_id': fields.many2one('mail.message', string='Message',
                        ondelete='cascade', required=True, select=1),
    }

    _defaults = {
        'read': False,
        'starred': False,
    }

    def init(self, cr):
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('mail_notification_partner_id_read_starred_message_id',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX mail_notification_partner_id_read_starred_message_id ON mail_notification (partner_id, read, starred, message_id)')

    def get_partners_to_notify(self, cr, uid, message, context=None):
        """ Return the list of partners to notify, based on their preferences.

            :param browse_record message: mail.message to notify
        """
        notify_pids = []
        for notification in message.notification_ids:
            if notification.read:
                continue
            partner = notification.partner_id
            # Do not send an email to the writer
            if partner.user_ids and partner.user_ids[0].id == uid:
                continue
            # Do not send to partners without email address defined
            if not partner.email:
                continue
            # Partner does not want to receive any emails
            if partner.notification_email_send == 'none':
                continue
            # Partner wants to receive only emails and comments
            if partner.notification_email_send == 'comment' and message.type not in ('email', 'comment'):
                continue
            # Partner wants to receive only emails
            if partner.notification_email_send == 'email' and message.type != 'email':
                continue
            notify_pids.append(partner.id)
        return notify_pids

    def get_signature_footer(self, cr, uid, user_id=None, res_model=None, res_id=None, context=None):
        footer = ""
        company = None
        user = None

        if user_id:
            users = self.pool.get("res.users").browse(cr, uid, [user_id], context=context)
            user = users and users[0] or None

        if user:
            if user.signature:
                signature = plaintext2html(user.signature)
            else:
                signature = "--<br>%s" % user.name
            footer = tools.append_content_to_html(footer, signature, plaintext=False, container_tag='p')

            if user.company_id:
                company = user.company_id.website and "<a style='color:inherit' href='%s'>%s</a>" % (user.company_id.website, user.company_id.name) or user.company_id.name
            else:
                company = user.name
        
        model_name = None
        record_name = None
        if res_model:
            res_model_obj = self.pool.get('ir.model')
            res_model_ids = res_model_obj.search(cr, uid, [('model', '=', res_model)], context=context)
            model_name = res_model_obj.browse(cr, uid, res_model_ids, context=context)[0].name
            if res_id:
                record_obj = self.pool.get(res_model)
                record = record_obj.browse(cr, uid, [res_id], context=context)[0]
                record_name = record.name_get() and record.name_get()[0] and record.name_get()[0][1] or record.name

        if company:
            if record_name:
                signature_company = _("This message is written on the document '<b>%(record_name)s</b>' of '<b>%(model_name)s</b>' from %(company)s." % {
                    'record_name': record_name, 
                    'model_name': model_name, 
                    'company': company
                })
            else:
                signature_company = _("This message is written from %(company)s." % {
                    'company': company
                })
            footer = tools.append_content_to_html(footer, "<small>%s</small>" % signature_company, plaintext=False, container_tag='div')
        else:
            if record_name:
                signature_company = _("This message is written on the document '<b>%(record_name)s</b>' of '<b>%(model_name)s</b>'." % {
                    'record_name': record_name, 
                    'model_name': model_name
                })
                footer = tools.append_content_to_html(footer, "<small>%s</small>" % signature_company, plaintext=False, container_tag='div')

        return footer

    def _notify(self, cr, uid, msg_id, context=None):
        """ Send by email the notification depending on the user preferences """
        if context is None:
            context = {}
        # mail_notify_noemail (do not send email) or no partner_ids: do not send, return
        if context.get('mail_notify_noemail'):
            return True
        # browse as SUPERUSER_ID because of access to res_partner not necessarily allowed
        msg = self.pool.get('mail.message').browse(cr, SUPERUSER_ID, msg_id, context=context)
        notify_partner_ids = self.get_partners_to_notify(cr, uid, msg, context=context)
        if not notify_partner_ids:
            return True

        # add the context in the email
        # TDE FIXME: commented, to be improved in a future branch
        # quote_context = self.pool.get('mail.message').message_quote_context(cr, uid, msg_id, context=context)

        # add signature
        body_html = msg.body
        user_id = msg.author_id and msg.author_id.user_ids and msg.author_id.user_ids[0] and msg.author_id.user_ids[0].id or None
        signature_company = self.get_signature_footer(cr, uid, user_id=user_id, res_model=msg.model, res_id=msg.res_id, context=context)
        body_html = tools.append_content_to_html(body_html, signature_company, plaintext=False, container_tag='div')

        mail_values = {
            'mail_message_id': msg.id,
            'email_to': [],
            'auto_delete': True,
            'body_html': body_html,
            'state': 'outgoing',
        }
        mail_values['email_to'] = ', '.join(mail_values['email_to'])
        mail_mail = self.pool.get('mail.mail')
        email_notif_id = mail_mail.create(cr, uid, mail_values, context=context)
        try:
            return mail_mail.send(cr, uid, [email_notif_id], recipient_ids=notify_partner_ids, context=context)
        except Exception:
            return False

