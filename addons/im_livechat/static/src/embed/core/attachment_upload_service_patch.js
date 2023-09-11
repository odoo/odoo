/* @odoo-module */

import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(AttachmentUploadService.prototype, {
    get uploadURL() {
        return `${session.origin}${super.uploadURL}`;
    },

    async uploadFile(thread, composer, file, options) {
        thread = await this.env.services["im_livechat.livechat"].persistThread();
        return super.uploadFile(
            thread,
            thread.type === "livechat" ? thread.composer : composer,
            file,
            options
        );
    },

    _makeFormData() {
        const formData = super._makeFormData(...arguments);
        const guestToken = this.env.services["im_livechat.livechat"].sessionCookie.guest_token;
        if (guestToken) {
            formData.append("guest_token", guestToken);
        }
    },
});
