import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { isEmbedLivechatEnabled } from "../common/misc";

patch(AttachmentUploadService.prototype, {
    get uploadURL() {
        if (!isEmbedLivechatEnabled(this.env)) {
            return super.uploadURL(...arguments);
        }
        return url("/im_livechat/cors/attachment/upload");
    },

    _makeFormData() {
        if (!isEmbedLivechatEnabled(this.env)) {
            return super._makeFormData(...arguments);
        }
        const formData = super._makeFormData(...arguments);
        formData.append("guest_token", this.env.services["im_livechat.livechat"].guestToken);
    },
});
