# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_by_email_get_base_mail_values(
        self,
        message,
        recipients_data,
        additional_values=None,
    ):
        ret = super()._notify_by_email_get_base_mail_values(
            message,
            recipients_data,
            additional_values,
        )
        if message.model == "forum.post" and "headers" in ret:
            # Can not force `_CUSTOMER_HEADERS_LIMIT_COUNT` to 0
            # because forum post does not inherit from `mail.thread`
            headers = ast.literal_eval(ret["headers"])
            headers.pop("X-Msg-To-Add", None)
            ret["headers"] = repr(headers)
        return ret

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message,
            model_description,
            msg_vals=msg_vals,
        )
        if message.model != "forum.post" or not message.res_id:
            return groups

        record = self.env["forum.post"].browse(message.res_id)
        if record.state == "active":
            for _group_name, _group_method, group_data in groups:
                group_data["has_button_access"] = True
        return groups
