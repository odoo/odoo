/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { Message as MessageModel } from "@mail/core/common/message_model";
import { Store } from "@mail/core/common/store_service";
import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { Thread } from "@mail/core/common/thread_model";
import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, "im_livechat/disabled", {
    get allowUpload() {
        return false;
    },
});

patch(MessageModel.prototype, "im_livechat/disabled", {
    get hasActions() {
        return false;
    },
});

patch(Thread.prototype, "im_livechat/disabled", {
    get hasMemberList() {
        return false;
    },
});

patch(ThreadService.prototype, "im_livechat/disabled", {
    async fetchNewMessages(thread) {
        return;
    },
    async loadAround() {
        return;
    },
});

patch(Store.prototype, "im_livechat/disabled", {
    setup() {
        this._super(...arguments);
        this.hasLinkPreviewFeature = false;
    },
});

const allowedThreadActions = new Set(["fold-chat-window", "close", "restart"]);
for (const [actionName] of threadActionsRegistry.getEntries()) {
    if (!allowedThreadActions.has(actionName)) {
        threadActionsRegistry.remove(actionName);
    }
}
threadActionsRegistry.addEventListener("UPDATE", ({ operation, key }) => {
    if (operation === "add" && !allowedThreadActions.has(key)) {
        threadActionsRegistry.remove(key);
    }
});
