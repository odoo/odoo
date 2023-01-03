/** @odoo-module **/

import { attr, one, Model } from "@mail/model";

Model({
    name: "ChatWindowHiddenMenuItemView",
    template: "mail.ChatWindowHiddenMenuItemView",
    fields: {
        chatWindowHeaderView: one("ChatWindowHeaderView", {
            identifying: true,
            inverse: "hiddenMenuItem",
        }),
        isLast: attr({
            default: false,
            compute() {
                return this.owner.lastItem === this;
            },
        }),
        owner: one("ChatWindowHiddenMenuView", { identifying: true, inverse: "items" }),
    },
});
