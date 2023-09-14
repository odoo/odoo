import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import "@portal/chatter/core/attachment_upload_service_patch";

import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadService.prototype, {
    _buildFormData(formData, tmpURL, thread, composer, tmpId, options) {
        super._buildFormData(...arguments);
        if (
            this.env.services["portal.chatter"]?.portalSecurity?.token &&
            thread.model !== "discuss.channel"
        ) {
            formData.append(
                "access_token",
                this.env.services["portal.chatter"].portalSecurity.token
            );
        }
        return formData;
    },
});
