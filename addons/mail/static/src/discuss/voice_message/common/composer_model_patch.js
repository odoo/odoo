import { Composer } from "@mail/core/common/composer_model";
import { patchModel } from "@mail/model/export";

export const composerPatch = patchModel(Composer, {
    /** @returns {import("models").Attachment|undefined} */
    get voiceAttachment() {
        return this.attachments.find((attachment) => attachment.voice);
    },
});
