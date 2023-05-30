/** @odoo-module */

import { ChatWindowService } from "@mail/chat_window/chat_window_service";
import { Composer } from "@mail/composer/composer";
import { Message as MessageModel } from "@mail/core/message_model";
import { Thread } from "@mail/core/thread_model";
import { patch } from "@web/core/utils/patch";
import { ThreadService } from "@mail/core/thread_service";
import { Store } from "@mail/core/store_service";

patch(ChatWindowService.prototype, "im_livechat/disabled", {
    notifyState() {
        return;
    },
});

patch(Composer.prototype, "im_livechat/disabled", {
    get allowUpload() {
        return false;
    },

    get allowEmojis() {
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
});

patch(Store.prototype, "im_livechat/disabled", {
    setup() {
        this._super(...arguments);
        this.hasLinkPreviewFeature = false;
    },
});
