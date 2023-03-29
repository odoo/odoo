/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, "discuss/voice_message/common", {
    get voiceDuration() {
        return this.duration;
    },
});
