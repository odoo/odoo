/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "CallSidebarViewTile",
    fields: {
        callSidebarViewOwner: one("CallSidebarView", {
            identifying: true,
            inverse: "sidebarTiles",
        }),
        channelMember: one("ChannelMember", { identifying: true }),
        participantCard: one("CallParticipantCard", {
            default: {},
            inverse: "sidebarViewTileOwner",
        }),
    },
});
