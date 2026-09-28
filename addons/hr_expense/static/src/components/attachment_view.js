import { patch } from "@web/core/utils/patch";
import { AttachmentView } from "@mail/core/common/attachment_view";

patch(AttachmentView.prototype, {
    get displayName() {
        if (this.props.thread().model === "hr.expense") {
            return this.props.thread().message_main_attachment_id.res_name || this.props.thread().name;
        }
        return super.displayName;
    },
});
