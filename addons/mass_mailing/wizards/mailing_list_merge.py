from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MailingListMerge(models.TransientModel):
    _name = "mailing.list.merge"
    _description = "Merge Mass Mailing List"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        if not res.get("src_list_ids") and "src_list_ids" in fields:
            if self.env.context.get("active_model") != "mailing.list":
                raise UserError(_("You can only apply this action from Mailing Lists."))
            src_list_ids = self.env.context.get("active_ids")
            res.update(
                {
                    "src_list_ids": [(6, 0, src_list_ids)],
                }
            )
        if not res.get("dest_list_id") and "dest_list_id" in fields:
            # From the context, not from `res["src_list_ids"]`: that is a command
            # list -- [(6, 0, ids)] -- so indexing it yields the command tuple
            # itself, and handing that to a many2one raises before the wizard can
            # be drawn. The ids are in the context either way, which is where the
            # block above got them.
            source_ids = self.env.context.get("active_ids") or []
            res["dest_list_id"] = source_ids[0] if source_ids else False
        return res

    src_list_ids = fields.Many2many(
        comodel_name="mailing.list",
        string="Mailing Lists",
    )
    dest_list_id = fields.Many2one(
        comodel_name="mailing.list",
        string="Destination Mailing List",
    )
    merge_options = fields.Selection(
        selection=[
            ("new", "Merge into a new mailing list"),
            ("existing", "Merge into an existing mailing list"),
        ],
        string="Merge Option",
        default="new",
        required=True,
    )
    new_list_name = fields.Char(string="New Mailing List Name")
    archive_src_lists = fields.Boolean(
        string="Archive source mailing lists",
        default=True,
    )

    def action_mailing_lists_merge(self):
        if self.merge_options == "new":
            self.dest_list_id = (
                self.env["mailing.list"]
                .create(
                    {
                        "name": self.new_list_name,
                    }
                )
                .id
            )
        self.dest_list_id.action_merge(self.src_list_ids, self.archive_src_lists)
        return self.dest_list_id
