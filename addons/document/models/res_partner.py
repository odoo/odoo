from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    document_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="partner_id",
        string="Documents",
    )
    document_count = fields.Integer(compute="_compute_document_count")

    def _compute_document_count(self) -> None:
        document_count_dict = dict(
            self.env["document.document"]._read_group(
                [("partner_id", "in", self.ids)],
                groupby=["partner_id"],
                aggregates=["__count"],
            )
        )

        _debug.perf.count("partner_document_counts", partners=self)
        for record in self:
            record.document_count = document_count_dict.get(record, 0)

    def action_see_documents(self) -> dict:
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "document.document_action_preference"
        )
        return action | {
            "domain": [("partner_id", "=", self.id)],
            "context": {
                "default_partner_id": self.id,
                "searchpanel_default_user_folder_id": False,
            },
        }
