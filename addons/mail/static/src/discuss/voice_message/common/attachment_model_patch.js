/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isViewable() {
        return !this.isVoice && super.isViewable;
    },
});

patch(Attachment, {
    update(attachment, data) {
        super.update(...arguments);
        if (data["voice"]) {
            attachment.isVoice = true;
        }
    },
});
