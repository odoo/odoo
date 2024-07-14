# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class SpreadsheetContributor(models.Model):
    _name = "spreadsheet.contributor"
    _description = "Spreadsheet Contributor"
    _rec_name = 'user_id'

    document_id = fields.Many2one("documents.document")
    user_id = fields.Many2one("res.users")
    last_update_date = fields.Datetime("Last update date", default=fields.Datetime.now)

    _sql_constraints = [
        (
            "spreadsheet_user_unique",
            "unique (document_id, user_id)",
            "A combination of the spreadsheet and the user already exist",
        ),
    ]

    @api.model
    def _update(self, user, document):
        record = self.search(
            [("user_id", "=", user.id), ("document_id", "=", document.id)]
        )
        if record:
            record.write({"last_update_date": fields.Datetime.now()})
        else:
            self.create(
                {
                    "document_id": document.id,
                    "user_id": user.id,
                }
            )
