import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { allowedThreadActions } from "@mail/core/common/thread_actions";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { isEmbedLivechatEnabled } from "./misc";

const downloadFilesAction = messageActionsRegistry.get("download_files");
patch(downloadFilesAction, {
    condition(component) {
        if (!isEmbedLivechatEnabled(component.env)) {
            return super.condition(...arguments);
        }
        return component.message.thread.channel_type !== "livechat" && super.condition(component);
    },
});

patch(Thread.prototype, {
    get hasMemberList() {
        if (!isEmbedLivechatEnabled(this._store.env)) {
            return super.hasMemberList;
        }
        return false;
    },
    get hasAttachmentPanel() {
        if (isEmbedLivechatEnabled(!this._store.env)) {
            return super.hasAttachmentPanel;
        }
        return this.channel_type !== "livechat" && super.hasAttachmentPanel;
    },
});

patch(allowedThreadActions, {
    fn(env) {
        const res = super.fn(...arguments);
        if (!isEmbedLivechatEnabled(env)) {
            return res;
        }
        return res.filter((id) =>
            ["fold-chat-window", "close", "restart", "settings"].includes(id)
        );
    },
});
