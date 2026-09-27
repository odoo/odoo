import { Composer } from "@mail/core/common/composer_model";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    /** @returns {import("models").Attachment|undefined} */
    get voiceAttachment() {
        return this.attachments.find((attachment) => attachment.voice);
    },
});
