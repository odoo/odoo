import {
    AttachmentUploadService,
    attachmentUploadService,
} from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadService.prototype, {
    setup(env, services) {
        super.setup(...arguments);
        /** @type {import("@portal/embed/frontend/portal_chatter_service").PortalChatterService} */
        this.portalChatterService = services["portal.chatter"];
    },

    _buildFormData(formData, file, thread, composer, tmpId, options) {
        super._buildFormData(...arguments);
        if (this.portalChatterService.token && thread.model != "discuss.channel") {
            formData.append("access_token", this.portalChatterService.token);
        }
        return formData;
    },
});

patch(attachmentUploadService, {
    dependencies: [...attachmentUploadService.dependencies, "portal.chatter"],
});
