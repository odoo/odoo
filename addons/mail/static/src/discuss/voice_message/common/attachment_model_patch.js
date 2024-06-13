import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isViewable() {
        return !this.voice && super.isViewable;
    },
    delete() {
        if (this.voice && this.id > 0) {
            this.store.env.services["discuss.voice_message"].activePlayer = null;
        }
        super.delete(...arguments);
    },
});
