import { Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class LinkPreviewMessage extends Record {
    static _name = "mail.link.preview.message";
    static id = "id";
    /** @returns {import("models").LinkPreview} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @returns {T extends any[] ? import("models").LinkPreview[] : import("models").LinkPreview}
     */
    static insert(data) {
        return super.insert(...arguments);
    }

    message_id = Record.one("mail.message", { inverse: "link_preview_message_ids" });
    link_preview_id = Record.one("mail.link.preview", { inverse: "link_preview_message_ids"});


    hide() {
        rpc(
            "/mail/link_preview/hide",
            {
                link_preview_message_ids: [this.id]
            },
            { silent: true }
        );
    }
}

LinkPreviewMessage.register();
