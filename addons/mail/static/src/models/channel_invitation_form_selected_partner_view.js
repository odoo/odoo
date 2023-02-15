/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "ChannelInvitationFormSelectedPartnerView",
    template: "mail.ChannelInvitationFormSelectedPartnerView",
    fields: {
        channelInvitationFormOwner: one("ChannelInvitationForm", {
            identifying: true,
            inverse: "selectedPartnerViews",
        }),
        partner: one("Partner", {
            identifying: true,
            inverse: "channelInvitationFormSelectedPartnerViews",
        }),
    },
});
