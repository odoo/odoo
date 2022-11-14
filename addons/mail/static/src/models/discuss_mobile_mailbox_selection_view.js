/** @odoo-module **/

import { many, one, Model } from "@mail/model";

Model({
    name: "DiscussMobileMailboxSelectionView",
    template: "mail.DiscussMobileMailboxSelectionView",
    fields: {
        items: many("DiscussMobileMailboxSelectionItemView", {
            inverse: "owner",
            compute() {
                return this.owner.orderedMailboxes.map((mailbox) => ({ mailbox }));
            },
        }),
        owner: one("DiscussView", { identifying: true, inverse: "mobileMailboxSelectionView" }),
    },
});
