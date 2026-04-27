from http import HTTPStatus

from odoo.http import request, route
from odoo.addons.documents.controllers.documents import ShareRoute


class HrShareRoute(ShareRoute):

    @route()
    def share_portal(self, share_id=None, token=None):
        # keep the old URLs working for backward compatibility
        redirect = (
            request.env["documents.redirect"]
            .sudo()
            .search([("access_token", "=", token), ("employee_id", "!=", False)])
        )
        if not redirect or not redirect.employee_id:
            return super().share_portal(share_id, token)
        return request.redirect(
            redirect.employee_id._get_documents_link_url(),
            code=HTTPStatus.MOVED_PERMANENTLY,
        )
