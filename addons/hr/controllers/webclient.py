# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler


class HrWebclientController(WebclientController):
    @store_handler("hr.employee.public")
    def store_hr_employee_public(self, store: Store, id):
        emp_public = request.env["hr.employee.public"].search_fetch([("id", "=", id)])
        store.add(emp_public, "_store_avatar_card_fields")

    @classmethod
    def _get_supported_avatar_card_models(self):
        return [*super()._get_supported_avatar_card_models(), "hr.employee", "hr.employee.public"]
