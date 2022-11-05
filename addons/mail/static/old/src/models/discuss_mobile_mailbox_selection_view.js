/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { many, one } from "@mail/model/model_field";

registerModel({
    name: "DiscussMobileMailboxSelectionView",
    template: "mail.DiscussMobileMailboxSelectionView",
    templateGetter: "discussMobileMailboxSelectionView",
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
