import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadService.prototype, {
    _makeAttachmentData(file, tmpId, thread, tmpUrl, formData) {
        const attachmentData = super._makeAttachmentData(...arguments);
        if (formData.get("voice")) {
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
