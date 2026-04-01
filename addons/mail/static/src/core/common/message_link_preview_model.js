import { fields, Record } from "@mail/core/common/record";

import { rpc } from "@web/core/network/rpc";

export class MessageLinkPreview extends Record {
    static _name = "mail.message.link.preview";
    static id = "id";

    message_id = fields.One("mail.message", { inverse: "message_link_preview_ids" });
    link_preview_id = fields.One("mail.link.preview", { inverse: "message_link_preview_ids" });

    get gifPaused() {
        return !this.message_id.thread?.isFocused;
    }

    hide() {
        rpc("/mail/link_preview/hide", { message_link_preview_ids: [this.id] });
    }
}

MessageLinkPreview.register();
