import { patch } from "@web/core/utils/patch";
import { AttachmentView } from "@mail/core/common/attachment_view";

patch(AttachmentView.prototype, {
    get displayName() {
        const thread = this.props.thread();
        if (thread.model === "hr.expense") {
            return thread.message_main_attachment_id.res_name || thread.name;
        }
        return super.displayName;
    },
});
