from odoo.http import route
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.controllers import thread

_debug = DebugLog(__name__)


class ThreadController(thread.ThreadController):
    @route()
    def mail_message_post(
        self, thread_model, thread_id, post_data, context=None, **kwargs
    ):
        _debug.pipeline("route", handler="ThreadController.mail_message_post")
        account_reports_annotation_date = post_data.pop(
            "account_reports_annotation_date", None
        )
        res = super().mail_message_post(
            thread_model, thread_id, post_data, context, **kwargs
        )
        if account_reports_annotation_date and res["store_data"]["mail.message"]:
            for message in res["store_data"]["mail.message"]:
                self.env["account.report.annotation"].create(
                    {
                        "message_id": message["id"],
                        "date": account_reports_annotation_date,
                    }
                )
                message["account_reports_annotation_date"] = (
                    account_reports_annotation_date
                )
        return res

    @route()
    def mail_message_update_content(self, message_id, update_data, **kwargs):
        _debug.pipeline("route", handler="ThreadController.mail_message_update_content")
        res = super().mail_message_update_content(message_id, update_data, **kwargs)
        message = self._get_message_with_access(message_id, mode="create", **kwargs)
        if message._filtered_empty():
            self.env["account.report.annotation"].sudo().search(
                [("message_id", "=", message_id)]
            ).unlink()
        return res
