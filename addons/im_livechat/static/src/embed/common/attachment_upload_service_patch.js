import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadService.prototype, {
    async upload(thread, composer, file, options) {
        if (thread.channel_type === "livechat" && thread.isTransient) {
            thread = await this.env.services["im_livechat.livechat"].persist(thread);
            if (!thread) {
                return;
            }
            thread.readyToSwapDeferred.resolve();
            composer = thread.composer;
        }
        return super.upload(thread, composer, file, options);
    },
});
