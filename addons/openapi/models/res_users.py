# Copyright 2018-2019 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2018 Rafis Bikbov <https://it-projects.info/team/bikbov>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import uuid

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    namespace_ids = fields.Many2many("openapi.namespace", string="Allowed Integrations")
    openapi_token = fields.Char(
        "OpenAPI Token",
        default=lambda self: self._get_unique_openapi_token(),
        required=True,
        copy=False,
        help="Authentication token for access to API (/api).",
    )

    def reset_openapi_token(self):
        for record in self:
            record.write({"openapi_token": self._get_unique_openapi_token()})

    def _get_unique_openapi_token(self):
        openapi_token = str(uuid.uuid4())
        while self.search_count([("openapi_token", "=", openapi_token)]):
            openapi_token = str(uuid.uuid4())
        return openapi_token

    @api.model
    def reset_all_openapi_tokens(self):
        self.search([]).reset_openapi_token()
