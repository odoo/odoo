# Copyright 2022 Manuel Regidor <manuel.regidor@sygel.es>
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class DocumentPage(models.Model):
    _inherit = "document.page"

    groups_id = fields.Many2many(comodel_name="res.groups", string="Groups")
    user_ids = fields.Many2many(comodel_name="res.users", string="Users")

    @api.constrains("groups_id", "user_ids")
    def check_document_page_groups_users(self):
        for _item in self.filtered(lambda x: x.groups_id and x.user_ids):
            raise UserError(
                self.env._("You cannot set groups and users at the same time.")
            )
        return True
