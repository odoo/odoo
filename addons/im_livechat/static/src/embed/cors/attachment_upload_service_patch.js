/* @odoo-module */

import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(AttachmentUploadService.prototype, {
    get uploadURL() {
        return url("/im_livechat/cors/attachment/upload");
    },

    _makeFormData() {
        const formData = super._makeFormData(...arguments);
        formData.append("guest_token", this.env.services["im_livechat.livechat"].guestToken);
    },
});
