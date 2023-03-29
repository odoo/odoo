/* @odoo-module */

import { setupAttachment } from "@mail/core/common/attachment_uploader_hook";

import { patch } from "@web/core/utils/patch";

patch(setupAttachment, "discuss/voice_message/common", {
    prepareFormData(formData, state, file, composer, tmpId, options) {
        this._super(...arguments);
        if (options?.voiceDuration) {
            formData.append("duration", options.voiceDuration);
        }
        return formData;
    },
    prepareAttachmentData(upload, tmpId, originThread, tmpUrl) {
        const attachmentData = this._super(...arguments);
        if (upload.data.get("duration")) {
            attachmentData.duration = upload.data.get("duration");
        }
        return attachmentData;
    },
});
