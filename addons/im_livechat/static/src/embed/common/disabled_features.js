import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get hasMemberList() {
        return false;
    },
    get hasAttachmentPanel() {
        return this.channel_type !== "livechat" && super.hasAttachmentPanel;
    },
});

const allowedThreadActions = new Set(["fold-chat-window", "close", "restart", "settings"]);
for (const [actionName] of threadActionsRegistry.getEntries()) {
    if (!allowedThreadActions.has(actionName)) {
        threadActionsRegistry.remove(actionName);
    }
}
threadActionsRegistry.addEventListener("UPDATE", ({ detail: { operation, key } }) => {
    if (operation === "add" && !allowedThreadActions.has(key)) {
        threadActionsRegistry.remove(key);
    }
});
