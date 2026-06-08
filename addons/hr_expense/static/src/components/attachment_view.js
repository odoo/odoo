import { patch } from "@web/core/utils/patch";
import { AttachmentView } from "@mail/core/common/attachment_view";

patch(AttachmentView.prototype, {
    get displayName() {
        if (this.thread().model === "hr.expense") {
            return this.thread().message_main_attachment_id.res_name || this.thread().name;
        }
        return super.displayName;
    },
});
