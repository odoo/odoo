import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup(...arguments);
        this.messagingMenuTabsAsMessages = fields.Many("MessagingMenuTab", { inverse: "messages" });
        this.assignComputed(
            "messagingMenuTabsAsMessages",
            function computeMessagingMenuTabsAsMessages() {
                return this.store.messagingMenu.allTabs.filter((tab) => tab.includesMessage(this));
            }
        );
    },
};
patch(Message.prototype, messagePatch);
