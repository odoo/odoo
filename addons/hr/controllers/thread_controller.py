from odoo.http import request, route

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import Store


class HRThreadController(ThreadController):
    @route()
    def mail_thread_messages(self, thread_model, thread_id, fetch_params=None):
        ret = super().mail_thread_messages(thread_model, thread_id, fetch_params)
        if thread_model != "hr.employee":
            return ret

        messages = request.env['mail.message'].browse(ret['messages'])
        for version_id in request.env['hr.employee'].browse(thread_id).version_ids:
            version_thread = self._get_thread_with_access("hr.version", version_id, mode="read")
            version_res = request.env["mail.message"]._message_fetch(domain=None, thread=version_thread, **(fetch_params or {}))
            messages |= version_res.pop("messages")

        if not request.env.user._is_public():
            messages.set_message_done()

        messages = messages.sorted(key=lambda m: -m.id)

        ret['data'] = Store().add(messages).get_result()
        ret['messages'] = messages.ids
        return ret
