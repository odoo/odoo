# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo.http import request

from odoo.addons.portal.controllers.portal_thread import PortalChatter
from .portal import ProjectCustomerPortal


class ProjectSharingChatter(PortalChatter):
    def _check_project_access_and_get_token(self, project_id, res_model, res_id, token):
        """ Check if the chatter in project sharing can be accessed

            If the portal user is in the project sharing, then we do not have the access token of the task
            but we can have the one of the project (if the user accessed to the project sharing views via the shared link).
            So, we need to check if the chatter is for a task and if the res_id is a task
            in the project shared. Then, if we had the project token and this one is the one in the project
            then we return the token of the task to continue the portal chatter process.
            If we do not have any token, then we need to check if the portal user is a follower of the project shared.
            If it is the case, then we give the access token of the task.
        """
        project_sudo = ProjectCustomerPortal._document_check_access(self, 'project.project', project_id, token)
        can_access = project_sudo and res_model == 'project.task' and project_sudo.with_user(request.env.user)._check_project_sharing_access()
        task = None
        if can_access:
            task = request.env['project.task'].sudo().with_context(active_test=False).search([('id', '=', res_id), ('project_id', '=', project_sudo.id)])
        if not can_access or not task:
            raise Forbidden()
        return task[task._mail_post_token_field]
