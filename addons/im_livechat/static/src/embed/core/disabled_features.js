/* @odoo-module */

import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { Thread } from "@mail/core/common/thread_model";
import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";
import { SESSION_STATE } from "./livechat_service";

const downloadFilesAction = messageActionsRegistry.get("download_files");
patch(downloadFilesAction, {
    condition(component) {
        return component.message.originThread.type !== "livechat" && super.condition(component);
    },
});

patch(Thread.prototype, {
    get hasMemberList() {
        return false;
    },
    get hasAttachmentPanel() {
        return this.type !== "livechat" && super.hasAttachmentPanel;
    },
});

patch(ThreadService.prototype, {
    async fetchNewMessages(thread) {
        if (thread.type !== "livechat" || this.livechatService.state === SESSION_STATE.PERSISTED) {
            return super.fetchNewMessages(...arguments);
        }
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
