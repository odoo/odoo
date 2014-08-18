# -*- coding: utf-8 -*-

import uuid

from openerp import SUPERUSER_ID
from openerp.tools.safe_eval import safe_eval as eval
from openerp.osv import osv
from openerp.osv import fields


class MailAction(osv.Model):
    """Mail Action Description """
    _name = 'mail.action'
    _description = 'Mail Action'

    _columns = {
        'name': fields.char('Label', required=True),
        'subtype_id': fields.many2one('mail.message.subtype', string='Subtype'),
        'server_action_id': fields.many2one('ir.actions.server', 'Server Action', required=True),
        'recipients': fields.selection([
            ('followers', 'All Followers'),
            ('subtype', 'Notified People'),
            ('custom', 'Custom Condition'),
        ], string='Recipients', required=True),
        'recipients_condition': fields.text('Pre Condition', help=''),
        'action_condition': fields.text('Action Condition', help=''),
    }

    def execute(self, cr, uid, ids, context=None):
        res = None
        for mail_action in self.browse(cr, uid, ids, context=context):
            if mail_action.action_condition:  # no condition is considered as True
                eval_context = self.pool['ir.actions.server']._get_eval_context(cr, uid, mail_action.server_action_id, context=context)
                expr = eval(str(mail_action.action_condition), eval_context)
                print '\t\tEvaluating expr', expr
                if not expr:
                    print '\t\tInvalidated', mail_action.action_condition
                    # continue
            res = mail_action.server_action_id.run()
        return res


class MailActionUser(osv.Model):
    _name = 'mail.action.user'
    _description = 'Action / Partner / Notification binding'
    _rec_name = 'mail_action_id'

    def _get_access_url(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = '/mail/action?token=%s&id=%s' % (obj.access_token, obj.id)
        return res

    _columns = {
        'mail_action_id': fields.many2one('mail.action', 'Mail Action', select=True),
        'partner_id': fields.many2one('res.partner', 'Recipient', select=True),
        'notification_id': fields.many2one('mail.notification', 'Notification', select=True),
        'access_token': fields.char('Invitation Token'),
        'access_url': fields.function(_get_access_url, type='char', string='Access URL'),
        'done': fields.boolean('Done'),
    }

    _defaults = {
        'access_token': lambda self, cr, uid, c=None: uuid.uuid4().hex
    }

    def execute(self, cr, uid, id, token, context=None):
        print '\tExecute from notification', uid, id, token
        act_user_ids = self.search(cr, uid, [('access_token', '=', token), ('id', '=', id), ('done', '=', False)], context=context)
        if not act_user_ids:
            print '\t\t-->Not found act_user_ids'
            return False

        act_user = self.browse(cr, SUPERUSER_ID, act_user_ids[0], context=context)
        eval_context = dict(
            context,
            active_id=act_user.notification_id.message_id.res_id,
            active_model=act_user.notification_id.message_id.model)
        res = self.pool['mail.action'].execute(
            cr, uid, [act_user.mail_action_id.id], context=eval_context)
        print '\tResult of execute form notification', res
        return res
