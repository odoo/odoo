import { AttachmentUploadPlugin } from "@mail/core/common/attachment_upload_plugin";

import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadPlugin.prototype, {
    _buildFormData(formData, file, thread, _composer, _tmpId, _options) {
        super._buildFormData(...arguments);
        if (thread.rpcParams.hash && thread.rpcParams.pid) {
            formData.append("hash", thread.rpcParams.hash);
            formData.append("pid", thread.rpcParams.pid);
        }
        if (thread.rpcParams.token) {
            formData.append("token", thread.rpcParams.token);
        }
        return formData;
    },
});
