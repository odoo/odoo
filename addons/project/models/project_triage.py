from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class ProjectTriage(models.Model):
    _name = "project.triage"
    _description = "Personal Task Triage Bucket"
    _inherit = ["mixin.project.pm"]
    _order = "sequence, id"

    active = fields.Boolean(
        export_string_translation=False,
        default=True,
    )
    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=1)
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    fold = fields.Boolean(string="Folded")
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Triage Owner",
        default=lambda self: self.env.user,
        index=True,
        required=True,
        ondelete="cascade",
    )

    @dbg.timed
    @api.ondelete(at_uninstall=False)
    def _unlink_if_remaining_triage_buckets(self) -> None:
        dbg.lifecycle.debug(
            "project.triage unlink %s for users %s", dbg.rec(self), self.user_id.ids
        )
        remaining_all = self.env["project.triage"]._read_group(
            [
                ("user_id", "in", self.user_id.ids),
                ("id", "not in", self.ids),
            ],
            groupby=["user_id", "sequence", "id"],
            order="user_id,sequence DESC",
        )
        remaining_by_user: dict = defaultdict(list)
        for user, sequence, bucket in remaining_all:
            remaining_by_user[user].append({"id": bucket.id, "seq": sequence})

        triage_to_update = self.env["project.task.triage"]._read_group(
            [("triage_id", "in", self.ids)],
            ["triage_id"],
            ["id:recordset"],
        )
        for user in self.user_id:
            if not user.active or user.share:
                dbg.logic.debug(
                    "project.triage unlink: user %s inactive/share, no replacement",
                    user.id,
                )
                continue
            user_buckets_to_unlink = self.filtered(lambda b, u=user: b.user_id == u)
            user_remaining = remaining_by_user[user]
            dbg.logic.debug(
                "project.triage unlink: user %s deleting %s, %d remaining buckets",
                user.id,
                dbg.rec(user_buckets_to_unlink),
                len(user_remaining),
            )
            if not user_remaining:
                raise UserError(
                    _(
                        "Each user must have at least one triage bucket. "
                        "Create a replacement bucket before deleting the selected ones."
                    )
                )
            user_buckets_to_unlink._update_task_triages_to_replacement(
                user_remaining, triage_to_update
            )

    def _update_task_triages_to_replacement(
        self, remaining_buckets: list[dict], triage_to_update
    ) -> None:
        buckets_to_delete = sorted(
            [{"id": b.id, "seq": b.sequence} for b in self],
            key=lambda b: b["seq"],
        )
        replacement_id = remaining_buckets.pop()["id"]
        next_replacement = remaining_buckets and remaining_buckets.pop()

        triage_by_bucket = {
            bucket.id: task_triages for bucket, task_triages in triage_to_update
        }
        for bucket in buckets_to_delete:
            while next_replacement and next_replacement["seq"] < bucket["seq"]:
                replacement_id = next_replacement["id"]
                next_replacement = remaining_buckets and remaining_buckets.pop()
            if bucket["id"] in triage_by_bucket:
                dbg.pipeline.debug(
                    "[triage:%s] -> moving %d task triages to bucket %s",
                    bucket["id"],
                    len(triage_by_bucket[bucket["id"]]),
                    replacement_id,
                )
                triage_by_bucket[bucket["id"]].triage_id = replacement_id
