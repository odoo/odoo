/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";

Model({
    name: "Mailbox",
    identifyingMode: "xor",
    recordMethods: {
        _onChangeCounter() {
            if (this !== this.messaging.inbox) {
                return;
            }
            if (
                this.thread.threadViews.length > 0 &&
                this.previousValueOfInboxCounter > 0 &&
                this.counter === 0
            ) {
                this.env.services.effect.add({
                    message: this.env._t("Congratulations, your inbox is empty!"),
                    type: "rainbow_man",
                });
            }
            this.update({ previousValueOfInboxCounter: this.counter });
        },
    },
    fields: {
        counter: attr({ default: 0 }),
        discussMobileSelectionItems: many("DiscussMobileMailboxSelectionItemView", {
            inverse: "mailbox",
        }),
        fetchMessagesUrl: attr({
            compute() {
                switch (this) {
                    case this.messaging.history:
                        return "/mail/history/messages";
                    case this.messaging.inbox:
                        return "/mail/inbox/messages";
                    case this.messaging.starred:
                        return "/mail/starred/messages";
                    default:
                        return clear();
                }
            },
        }),
        /**
         * Useful to fill its inverse `Messaging/allMailboxes`.
         */
        messagingAsAnyMailbox: one("Messaging", {
            inverse: "allMailboxes",
            compute() {
                if (!this.messaging) {
                    return clear();
                }
                return this.messaging;
            },
        }),
        messagingAsHistory: one("Messaging", { identifying: true, inverse: "history" }),
        messagingAsInbox: one("Messaging", { identifying: true, inverse: "inbox" }),
        messagingAsStarred: one("Messaging", { identifying: true, inverse: "starred" }),
        name: attr({
            compute() {
                switch (this) {
                    case this.messaging.history:
                        return this.env._t("History");
                    case this.messaging.inbox:
                        return this.env._t("Inbox");
                    case this.messaging.starred:
                        return this.env._t("Starred");
                    default:
                        return clear();
                }
            },
        }),
        /**
         * Useful to display rainbow man on inbox.
         */
        previousValueOfInboxCounter: attr({ default: 0 }),
        sequence: attr({
            compute() {
                switch (this) {
                    case this.messaging.history:
                        return 2;
                    case this.messaging.inbox:
                        return 0;
                    case this.messaging.starred:
                        return 1;
                    default:
                        return clear();
                }
            },
        }),
        thread: one("Thread", {
            inverse: "mailbox",
            compute() {
                const threadId = (() => {
                    switch (this) {
                        case this.messaging.history:
                            return "history";
                        case this.messaging.inbox:
                            return "inbox";
                        case this.messaging.starred:
                            return "starred";
                    }
                })();
                if (!threadId) {
                    return clear();
                }
                return {
                    id: threadId,
                    model: "mail.box",
                };
            },
        }),
    },
    onChanges: [
        {
            dependencies: ["counter"],
            methodName: "_onChangeCounter",
        },
    ],
});
