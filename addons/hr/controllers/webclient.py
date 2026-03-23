# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store
from odoo.http import request


class HrWebclientController(WebclientController):
    @classmethod
    def _process_request_for_internal_user(cls, store: Store, name, params):
        super()._process_request_for_internal_user(store, name, params)
        if name == "hr.employee.public":
            emp_public = request.env["hr.employee.public"].search_fetch([("id", "=", params["id"])])
            store.add(emp_public, "_store_avatar_card_fields")

    @classmethod
    def _get_supported_avatar_card_models(self):
        return [*super()._get_supported_avatar_card_models(), "hr.employee", "hr.employee.public"]
