/* @odoo-module */

import { ChatWindowService } from "@mail/core/common/chat_window_service";
import { Composer } from "@mail/core/common/composer";
import { Message as MessageModel } from "@mail/core/common/message_model";
import { Store } from "@mail/core/common/store_service";
import { Thread } from "@mail/core/common/thread_model";
import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";

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
