/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { one } from "@mail/model/model_field";

registerModel({
    name: "DiscussMobileMailboxSelectionItemView",
    template: "mail.DiscussMobileMailboxSelectionItemView",
    templateGetter: "discussMobileMailboxSelectionItemView",
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
