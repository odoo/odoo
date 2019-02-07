# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo.addons.mail.controllers.main import MailController
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools.misc import consteq


class MailController(MailController):

    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None):
        # If the current user doesn't have access to the sales order, but provided
        # a valid access token, redirect him to the front-end view.
        if model == 'sale.order' and res_id and access_token:
            uid = request.session.uid or request.env.ref('base.public_user').id
            record_sudo = request.env[model].sudo().browse(res_id).exists()
            try:
                record_sudo.sudo(uid).check_access_rights('read')
                record_sudo.sudo(uid).check_access_rule('read')
            except AccessError:
                if record_sudo.access_token and consteq(record_sudo.access_token, access_token):
                    record_action = record_sudo.with_context(
                        force_website=True).get_access_action()
                    if record_action['type'] == 'ir.actions.act_url':
                        return werkzeug.utils.redirect(record_action['url'])
        return super(MailController, cls)._redirect_to_record(model, res_id, access_token=access_token)
