/** @odoo-module **/

import { clear, one, Model } from "@mail/model";

Model({
    name: "DiscussSidebarMailboxView",
    template: "mail.DiscussSidebarMailboxView",
    identifyingMode: "xor",
    fields: {
        discussViewOwnerAsHistory: one("DiscussView", {
            identifying: true,
            inverse: "historyView",
        }),
        discussViewOwnerAsInbox: one("DiscussView", { identifying: true, inverse: "inboxView" }),
        discussViewOwnerAsStarred: one("DiscussView", {
            identifying: true,
            inverse: "starredView",
        }),
        mailbox: one("Mailbox", {
            required: true,
            compute() {
                if (this.discussViewOwnerAsHistory) {
                    return this.messaging.history;
                }
                if (this.discussViewOwnerAsInbox) {
                    return this.messaging.inbox;
                }
                if (this.discussViewOwnerAsStarred) {
                    return this.messaging.starred;
                }
                return clear();
            },
        }),
        threadIconView: one("ThreadIconView", {
            default: {},
            inverse: "discussSidebarMailboxViewOwner",
        }),
    },
});
