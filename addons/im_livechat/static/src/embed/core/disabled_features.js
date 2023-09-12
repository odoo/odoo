/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { Store } from "@mail/core/common/store_service";
import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { Thread } from "@mail/core/common/thread_model";
import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";
import { SESSION_STATE } from "./livechat_service";

patch(Composer.prototype, {
    get allowUpload() {
        return false;
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

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.hasLinkPreviewFeature = false;
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
