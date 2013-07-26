# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013 OpenERP S.A. <http://www.openerp.com>
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

from openerp.osv import fields, osv


class actions_server(osv.Model):
    """ Add email option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    def _get_states(self, cr, uid, context=None):
        res = super(actions_server, self)._get_states(cr, uid, context=context)
        res.insert(0, ('email', 'Send Email'))
        return res

    _columns = {
        'email_from': fields.char('From',
                                  help="Sender address; define the template to see its value. If not set, the default "
                                  "value will be the author's email alias if configured, or email address."),
        'email_to': fields.char('To (Emails)',
                                help="Comma-separated recipient addresses; define the template to see its value"),
        'partner_to': fields.char('To (Partners)',
                                  help="Comma-separated ids of recipient partners; define the template to see its value"),
        'subject': fields.char('Subject',
                               help="Email subject; define the template to see its value"),
        'body_html': fields.text('Body',
                                 help="Rich-text/HTML version of the message; define the template to see its value"),
        'template_id': fields.many2one('email.template', 'Email Template', ondelete='set null',
                                       help="Define the email template to use for the email to send.")
    }

    def on_change_template_id(self, cr, uid, ids, template_id, context=None):
        """ Render the raw template in the server action fields. """
        if template_id:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'attachment_ids']
            template_values = self.pool.get('email.template').read(cr, uid, template_id, fields, context)
            values = dict((field, template_values[field]) for field in fields if template_values.get(field))
            if not values.get('email_from'):
                return {'warning': {'title': 'Incomplete template', 'message': 'Your template should define email_from'}, 'value': values}
        else:
            values = self.default_get(cr, uid, ['subject', 'body_html', 'email_from', 'email_to', 'partner_to'], context=context)

        return {'value': values}

    def create(self, cr, uid, values, context=None):
        if values.get('template_id'):
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'attachment_ids']
            template_values = self.pool.get('email.template').read(cr, uid, values.get('template_id'), fields, context)
            values.update(dict((field, template_values[field]) for field in fields if template_values.get(field)))
        return super(actions_server, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if values.get('template_id'):
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'attachment_ids']
            template_values = self.pool.get('email.template').read(cr, uid, values.get('template_id'), fields, context)
            values.update(dict((field, template_values[field]) for field in fields if template_values.get(field)))
        return super(actions_server, self).write(cr, uid, ids, values, context=context)

    def run_action_email(self, cr, uid, action, eval_context=None, context=None):
        if not action.template_id or not context.get('active_id'):
            return False
        self.pool['email.template'].send_mail(cr, uid, action.template_id.id, context.get('active_id'),
                                              force_send=False, raise_exception=False, context=context)
        return False


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
