import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(AttachmentUploadService.prototype, {
    getUploadURL(thread) {
        if (thread.channel_type === "livechat") {
            return url("/im_livechat/cors/attachment/upload");
        }
        return super.getUploadURL(...arguments);
    },

    _buildFormData() {
        const formData = super._buildFormData(...arguments);
        formData.append("guest_token", this.env.services["im_livechat.livechat"].guestToken);
    },
});
