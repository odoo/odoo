/** @odoo-module native */
import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";
import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadService.prototype, {
    _updateFormData(formData, file, thread, composer, tmpId, options) {
        super._updateFormData(...arguments);
        const { hash, pid, token } = thread.rpcParams;
        if (hash && pid) {
            formData.append("hash", hash);
            formData.append("pid", pid);
        }
        if (token) {
            formData.append("token", token);
        }
        return formData;
    },
});
