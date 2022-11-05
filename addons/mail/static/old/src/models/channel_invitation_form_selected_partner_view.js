/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { one } from "@mail/model/model_field";

registerModel({
    name: "ChannelInvitationFormSelectedPartnerView",
    template: "mail.ChannelInvitationFormSelectedPartnerView",
    templateGetter: "channelInvitationFormSelectedPartnerView",
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
