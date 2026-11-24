import { AttachmentUploadPlugin } from "@mail/core/common/attachment_upload_plugin";

import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadPlugin.prototype, {
    _makeAttachmentData(upload, tmpId, thread, tmpUrl) {
        const attachmentData = super._makeAttachmentData(...arguments);
        if (upload.data.get("voice")) {
            attachmentData.voice_ids = [this.store["discuss.voice.metadata"].insert({ id: -1 })];
        }
        return attachmentData;
    },
    _buildFormData(formData, tmpURL, thread, composer, tmpId, options) {
        super._buildFormData(...arguments);
        if (options?.voice) {
            formData.append("voice", true);
        }
        return formData;
    },
});
