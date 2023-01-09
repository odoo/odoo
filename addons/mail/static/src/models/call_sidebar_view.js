/** @odoo-module **/

import { many, one, Model } from "@mail/model";

Model({
    name: "CallSidebarView",
    template: "mail.CallSidebarView",
    fields: {
        callView: one("CallView", { identifying: true, inverse: "callSidebarView" }),
        sidebarTiles: many("CallSidebarViewTile", {
            inverse: "callSidebarViewOwner",
            compute() {
                return this.callView.filteredChannelMembers.map((channelMember) => ({
                    channelMember,
                }));
            },
        }),
    },
});
