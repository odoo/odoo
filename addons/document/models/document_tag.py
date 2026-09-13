from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DocumentsTag(models.Model):
    _name = "document.tag"
    _description = "Tag"
    _inherit = ["mixin.tag"]
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    tooltip = fields.Char(help="Text shown when hovering on this tag")
    document_ids = fields.Many2many(
        comodel_name="document.document",
        relation="document_tag_rel",
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_in_server_action(self) -> None:
        resource_refs = [f"document.tag,{tag_id}" for tag_id in self.ids]
        if resource_refs and self.env["ir.actions.server"].search_count(
            [("resource_ref", "in", resource_refs)], limit=1
        ):
            raise UserError(_("You cannot delete tags used in server actions."))
