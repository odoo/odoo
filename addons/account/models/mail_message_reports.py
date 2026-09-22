from odoo import models

from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _to_store_defaults(self, target):
        if any(
            m.model in self.env["report.formula"]._get_annotatable_models()
            for m in self
        ) and self.env["account.report.annotation"].has_access("read"):
            message_id_to_annotation_date = {
                a["message_id"][0]: a["date"]
                for a in self.env["account.report.annotation"].search_read(
                    [("message_id", "in", self.ids)],
                    ["message_id", "date"],
                )
            }
        else:
            message_id_to_annotation_date = {}
        return super()._to_store_defaults(target) + [
            Store.Attr(
                "account_reports_annotation_date",
                value=lambda m: message_id_to_annotation_date.get(m.id),
                predicate=lambda m: (
                    m.model in self.env["report.formula"]._get_annotatable_models()
                ),
            )
        ]
