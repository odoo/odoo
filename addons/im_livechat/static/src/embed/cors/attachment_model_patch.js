import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Attachment} */
const attachmentPatch = {
    get urlQueryParams() {
        return {
            ...super.urlQueryParams,
            guest_token: this.store.env.services["im_livechat.livechat"].guestToken,
        };
    },
    get urlRoute() {
        if (!this.access_token && this.thread?.model === "discuss.channel") {
            return this.isImage
                ? `/im_livechat/cors/channel/${this.thread.id}/image/${this.id}`
                : `/im_livechat/cors/channel/${this.thread.id}/attachment/${this.id}`;
        }
        return super.urlRoute;
    },
};
patch(Attachment.prototype, attachmentPatch);
