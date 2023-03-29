/* @odoo-module */

import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadService.prototype, {
    _makeAttachmentData(upload, tmpId, originThread, tmpUrl) {
        const attachmentData = super._makeAttachmentData(...arguments);
        if (upload.data.get("voice")) {
            attachmentData.voice = upload.data.get("voice");
        }
        return attachmentData;
    },
    _makeFormData(formData, file, hooker, tmpId, options) {
        super._makeFormData(...arguments);
        if (options?.isVoice) {
            formData.append("voice", options.isVoice);
        }
        return formData;
    },
});
