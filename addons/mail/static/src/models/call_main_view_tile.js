/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "CallMainViewTile",
    fields: {
        callMainViewOwner: one("CallMainView", { identifying: true, inverse: "mainTiles" }),
        channelMember: one("ChannelMember", { identifying: true }),
        participantCard: one("CallParticipantCard", { default: {}, inverse: "mainViewTileOwner" }),
    },
});
