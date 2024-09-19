import { Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class MessageLinkPreview extends Record {
    static _name = "mail.message.link.preview";
    static id = "id";
    /** @returns {import("models").MessageLinkPreview} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @returns {T extends any[] ? import("models").MessageLinkPreview[] : import("models").MessageLinkPreview}
     */
    static insert(data) {
        return super.insert(...arguments);
    }

    message_id = Record.one("mail.message", { inverse: "message_link_preview_ids" });
    link_preview_id = Record.one("mail.link.preview", { inverse: "message_link_preview_ids" });

    hide() {
        rpc("/mail/link_preview/hide", {
            message_link_preview_ids: [this.id],
        });
    }
}

MessageLinkPreview.register();
