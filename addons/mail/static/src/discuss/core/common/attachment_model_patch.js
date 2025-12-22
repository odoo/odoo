import { Attachment } from "@mail/core/common/attachment_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Attachment} */
const attachmentPatch = {
    get isDeletable() {
        if (
            this.thread?.channel &&
            this.store.self_user?.share === false &&
            !this.store.self_user.is_admin &&
            !this.message_ids.some((m) => m.isSelfAuthored) &&
            !["admin", "owner"].includes(this.thread?.self_member_id?.channel_role)
        ) {
            return false;
        }
        return super.isDeletable;
    },
};
patch(Attachment.prototype, attachmentPatch);
