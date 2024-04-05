import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { Record } from "../common/record";
import { assignDefined } from "@mail/utils/common/misc";

patch(Thread.prototype, {
    /** @type {integer|undefined} */
    recipientsCount: undefined,
    setup() {
        super.setup();
        this.recipients = Record.many("Follower");
        this.activities = Record.many("Activity", {
            sort: (a, b) => {
                if (a.date_deadline === b.date_deadline) {
                    return a.id - b.id;
                }
                return a.date_deadline < b.date_deadline ? -1 : 1;
            },
            onDelete(r) {
                r.delete();
            },
        });
    },
    get recipientsFullyLoaded() {
        return this.recipientsCount === this.recipients.length;
    },
    async leave() {
        this.closeChatWindow();
        super.leave(...arguments);
    },
    open(replaceNewMessageChatWindow, options) {
        if (!this.store.discuss.isActive && !this.store.env.services.ui.isSmall) {
            this._openChatWindow(replaceNewMessageChatWindow, options);
            return;
        }
        if (this.store.env.services.ui.isSmall && this.model === "discuss.channel") {
            this._openChatWindow(replaceNewMessageChatWindow, options);
            return;
        }
        if (this.model !== "discuss.channel") {
            this.store.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_id: this.id,
                res_model: this.model,
                views: [[false, "form"]],
            });
            return;
        }
        super.open(replaceNewMessageChatWindow);
    },
    async unpin() {
        const chatWindow = this.store.discuss.chatWindows.find((c) => c.thread?.eq(this));
        if (chatWindow) {
            await chatWindow.close();
        }
        super.unpin(...arguments);
    },
    _openChatWindow(replaceNewMessageChatWindow, { openMessagingMenuOnClose } = {}) {
        const chatWindow = this.store.ChatWindow.insert(
            assignDefined(
                {
                    folded: false,
                    replaceNewMessageChatWindow,
                    thread: this,
                },
                { openMessagingMenuOnClose }
            )
        );
        chatWindow.autofocus++;
        this.state = "open";
        chatWindow.notifyState();
    },
});
