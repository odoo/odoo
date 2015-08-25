from operator import itemgetter
import psycopg2

import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request


class MailController(http.Controller):
    _cp_path = '/mail'

    @http.route('/mail/receive', type='json', auth='none')
    def receive(self, req):
        """ End-point to receive mail from an external SMTP server. """
        dbs = req.jsonrequest.get('databases')
        for db in dbs:
            message = dbs[db].decode('base64')
            try:
                registry = openerp.registry(db)
                with registry.cursor() as cr:
                    mail_thread = registry['mail.thread']
                    mail_thread.message_process(cr, SUPERUSER_ID, None, message)
            except psycopg2.Error:
                pass
        return True

    @http.route('/mail/read_followers', type='json', auth='user')
    def read_followers(self, follower_ids):
        result = []
        is_editable = request.env.user.has_group('base.group_no_one')
        for follower in request.env['mail.followers'].browse(follower_ids):
            result.append({
                'id': follower.id,
                'name': follower.partner_id.name or follower.channel_id.name,
                'res_model': 'res.partner' if follower.partner_id else 'mail.channel',
                'res_id': follower.partner_id.id or follower.channel_id.id,
                'is_editable': is_editable,
                'is_uid': request.env.user.partner_id == follower.partner_id,
            })
        return result

    @http.route('/mail/read_subscription_data', type='json', auth='user')
    def read_subscription_data(self, res_model, res_id):
        """ Computes:
            - message_subtype_data: data about document subtypes: which are
                available, which are followed if any """
        # find the document followers, update the data
        followers = request.env['mail.followers'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('res_id', '=', res_id),
            ('res_model', '=', res_model),
        ])

        # find current model subtypes, add them to a dictionary
        subtypes = request.env['mail.message.subtype'].search(['&', ('hidden', '=', False), '|', ('res_model', '=', res_model), ('res_model', '=', False)])
        subtypes_list = [{
            'name': subtype.name,
            'res_model': subtype.res_model,
            'sequence': subtype.sequence,
            'default': subtype.default,
            'internal': subtype.internal,
            'followed': subtype.id in followers.mapped('subtype_ids').ids,
            'parent_model': subtype.parent_id and subtype.parent_id.res_model or False,
            'id': subtype.id
        } for subtype in subtypes]
        subtypes_list = sorted(subtypes_list, key=itemgetter('parent_model', 'res_model', 'internal', 'sequence'))

        return subtypes_list
