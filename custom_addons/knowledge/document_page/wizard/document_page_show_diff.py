# Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError


class DocumentPageShowDiff(models.TransientModel):
    """Display Difference for History."""

    _name = "wizard.document.page.history.show_diff"
    _description = "Document Page Show Diff"

    def _get_diff(self):
        """Return the Difference between two documents"""
        history = self.env["document.page.history"]
        ids = self.env.context.get("active_ids", [])
        diff = False
        if len(ids) == 2:
            if ids[0] > ids[1]:
                diff = history._get_diff(ids[1], ids[0])
            else:
                diff = history._get_diff(ids[0], ids[1])
        elif len(ids) == 1:
            diff = history.browse(ids[0]).diff
        else:
            raise UserError(self.env._("Select one or maximum two history revisions!"))
        return diff

    diff = fields.Html(readonly=True, default=_get_diff, sanitize_tags=False)
