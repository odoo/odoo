import { patch } from "@web/core/utils/patch";
import { MailThread } from "@mail/../tests/mock_server/mock_models/mail_thread";

patch(MailThread.prototype, {
    /**
     * @override
     */
    async _get_mail_thread_data(id, request_list) {
        const res = await super._get_mail_thread_data(id, request_list);
        if (res.model === "hr.expense.sheet" && request_list.includes("attachments")) {
            const HrExpenseSheet = this.env["hr.expense.sheet"];
            const IrAttachment = this.env["ir.attachment"];
            const [sheet] = HrExpenseSheet.search_read([
                ["id", "=", res.id],
            ]);
            const attachments_ids = IrAttachment.search_read([
                ["res_id", "in", sheet.expense_line_ids],
                ["res_model", "=", "hr.expense"],
            ]).map(a => a.id);
            if (Array.isArray(res["attachments"])) {
                res["attachments"] = IrAttachment._attachment_format(attachments_ids);
            } else {
                res["attachments"].push(IrAttachment._attachment_format(attachments_ids));
            }
            return res;
        }
        return res;
    }
});
