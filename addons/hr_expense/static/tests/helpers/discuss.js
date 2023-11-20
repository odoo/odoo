/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _mockRouteMailThreadData(thread_model, thread_id, request_list) {
        if (thread_model === "hr.expense.sheet" && request_list.includes("attachments")) {
            const res = await super._mockRouteMailThreadData(thread_model, thread_id, request_list);
            const sheet = this.pyEnv["hr.expense.sheet"].searchRead([
                ["id", "=", thread_id],
            ]);
            const attachments = this.pyEnv["ir.attachment"].searchRead([
                ["res_id", "in", sheet[0].expense_line_ids],
                ["res_model", "=", "hr.expense"],
            ]);
            if (Array.isArray(res["attachments"])) {
                res["attachments"] = this._mockIrAttachment_attachmentFormat(attachments.map((attachment) => attachment.id));
            } else {
                res["attachments"].push(this._mockIrAttachment_attachmentFormat(attachments.map((attachment) => attachment.id)));
            }
            return res;
        }
        return super._mockRouteMailThreadData(thread_model, thread_id, request_list);
    }
});
