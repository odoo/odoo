# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest

from odoo import api, models, registry, SUPERUSER_ID
from odoo.http import request

from odoo.addons.calendar.models.calendar import calendar_id2real_id, get_real_ids


class IrValues(models.Model):
    _inherit = 'ir.values'

    @api.model
    def set(self, key, key2, name, models, value, replace=True, isobject=False, meta=False, preserve_user=False, company=False):
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], calendar_id2real_id(data[1])))
            else:
                new_model.append(data)
        return super(IrValues, self).set(key, key2, name, new_model,
                                          value, replace, isobject, meta, preserve_user, company)

    @api.model
    def get(self, key, key2, models, meta=False, res_id_req=False, without_user=True, key2_req=True):
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], calendar_id2real_id(data[1])))
            else:
                new_model.append(data)
        return super(IrValues, self).get(key, key2, new_model,
                                          meta, res_id_req, without_user, key2_req)

class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        args = list(args)
        if any([leaf for leaf in args if leaf[0] ==  "res_model" and leaf[2] == 'calendar.event']):
            for index in range(len(args)):
                if args[index][0] == "res_id" and isinstance(args[index][2], basestring):
                    args[index] = (args[index][0], args[index][1], get_real_ids(args[index][2]))
        return super(IrAttachment, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.multi
    def write(self, vals):
        '''
        when posting an attachment (new or not), convert the virtual ids in real ids.
        '''
        if isinstance(vals.get('res_id'), basestring):
            vals['res_id'] = get_real_ids(vals.get('res_id'))
        return super(IrAttachment, self).write(vals)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _auth_method_calendar(self):
        token = request.params['token']
        db = request.params['db']

        error_message = False
        with registry(db).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, context={})
            attendee = env['calendar.attendee'].search([('access_token', '=', token)], limit=1)
            if not attendee:
                error_message = """Invalid Invitation Token."""
            elif request.session.uid and request.session.login != 'anonymous':
                 # if valid session but user is not match
                user = env['res.users'].browse(request.session.uid)
                if attendee.partner_id != user.partner_id:
                    error_message = """Invitation cannot be forwarded via email. This event/meeting belongs to %s and you are logged in as %s. Please ask organizer to add you.""" % (attendee.email, user.email)

        if error_message:
            raise BadRequest(error_message)

        return True
