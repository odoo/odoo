# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden
from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers import thread
from odoo.addons.portal.controllers.portal import CustomerPortal


class ThreadController(thread.ThreadController):

    @http.route()
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        project_sharing_id = kwargs.get("project_sharing_id")
        if project_sharing_id:
            project_sudo = CustomerPortal._document_check_access(self, "project.project", project_sharing_id, None)
            can_access = project_sudo and thread_model == "project.task" and project_sudo.with_user(
                request.env.user)._check_project_sharing_access()
            task = None
            if can_access:
                task = request.env["project.task"].sudo().search(
                    [("id", "=", thread_id), ("project_id", '=', project_sudo.id)])
            if not can_access or not task:
                raise Forbidden()
            token = task[task._mail_post_token_field]
            if token:
                request.env.context = {**request.env.context, "portal_token": token}
        return super().mail_message_post(thread_model, thread_id, post_data, context, **kwargs)
