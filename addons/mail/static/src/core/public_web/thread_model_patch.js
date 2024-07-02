import { patch } from "@web/core/utils/patch";
import { Thread } from "@mail/core/common/thread_model";
import { Record } from "@mail/core/common/record";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.discussAppCategory = Record.one("DiscussAppCategory", {
            compute() {
                return this._computeDiscussAppCategory();
            },
        });
    },

    _computeDiscussAppCategory() {
        if (["group", "chat"].includes(this.channel_type)) {
            return this.store.discuss.chats;
        }
        if (this.channel_type === "channel") {
            return this.store.discuss.channels;
        }
    },
});
