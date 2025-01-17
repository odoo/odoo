import { ChatHub } from "@mail/core/common/chat_hub_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChatHub} */
const chatHubPatch = {
    initThread(threadData) {
        if (threadData.model === "discuss.channel") {
            this.store.fetchChannel(threadData.id);
        } else {
            super.initThread(...arguments);
        }
    },
};
patch(ChatHub.prototype, chatHubPatch);
