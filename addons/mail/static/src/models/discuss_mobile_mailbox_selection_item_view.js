/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "DiscussMobileMailboxSelectionItemView",
    template: "mail.DiscussMobileMailboxSelectionItemView",
    recordMethods: {
        onClick() {
            if (!this.exists()) {
                return;
            }
            this.mailbox.thread.open();
        },
    },
    fields: {
        mailbox: one("Mailbox", { identifying: true, inverse: "discussMobileSelectionItems" }),
        owner: one("DiscussMobileMailboxSelectionView", { identifying: true, inverse: "items" }),
    },
});
