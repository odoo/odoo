import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isViewable() {
        return !this.voice && super.isViewable;
    },
});
