import { Message } from "@mail/core/common/message_model";
import { patchModel } from "@mail/model/export";
import { fields } from "@mail/model/misc";

export const messagePatch = patchModel(Message, {
    setup() {
        super.setup(...arguments);
        this.messagingMenuTabsAsMessages = fields.Many("MessagingMenuTab", {
            inverse: "messages",
            /** @this {import("models").Message} */
            compute() {
                return this.store.messagingMenu.allTabs.filter((tab) => tab.includesMessage(this));
            },
            eager: true,
        });
    },
});
