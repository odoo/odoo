from odoo.http import request
from odoo.tools import consteq

from odoo.addons.portal.controllers.mail import MailController


class ProjectMailController(MailController):

    @classmethod
    def _redirect_to_generic_fallback(cls, model, res_id, access_token=None, **kwargs):
        if model in ('project.project', 'project.task') and access_token and request.session.uid and request.env.user.share:
            record_sudo = request.env[model].sudo().browse(res_id).exists()
            if record_sudo and record_sudo.access_token and not consteq(record_sudo.access_token, access_token):
                return request.redirect_query('/my', {'access_error': 1})
        return super()._redirect_to_generic_fallback(model, res_id, access_token=access_token, **kwargs)

    @classmethod
    def _redirect_to_login_with_mail_view(cls, model, res_id, access_token=None, **kwargs):
        if model in ('project.project', 'project.task') and access_token:
            record_sudo = request.env[model].sudo().browse(res_id).exists()
            if record_sudo and record_sudo.access_token and not consteq(record_sudo.access_token, access_token):
                return request.redirect_query('/web/login', {'access_error': 1})
        return super()._redirect_to_login_with_mail_view(model, res_id, access_token=access_token, **kwargs)
