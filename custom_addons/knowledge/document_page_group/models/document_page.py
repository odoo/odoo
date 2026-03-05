# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class DocumentPage(models.Model):
    _inherit = "document.page"

    group_ids = fields.Many2many(
        "res.groups",
        store=True,
        recursive=True,
        relation="document_page_direct_group",
        column1="document_page_id",
        column2="group_id",
        compute="_compute_group_ids",
    )
    direct_group_ids = fields.Many2many(
        "res.groups",
        string="Visible to",
        help="Set the groups that can view this category and its childs",
        relation="document_page_group",
        column1="document_page_id",
        column2="group_id",
    )

    @api.depends("direct_group_ids", "parent_id", "parent_id.group_ids")
    def _compute_group_ids(self):
        for record in self:
            groups = record.direct_group_ids
            if record.parent_id:
                groups |= record.parent_id.group_ids
            record.group_ids = groups
