/** @odoo-module **/

import { clear, one, Model } from "@mail/model";

Model({
    name: "ChannelInvitationFormSelectablePartnerView",
    template: "mail.ChannelInvitationFormSelectablePartnerView",
    fields: {
        channelInvitationFormOwner: one("ChannelInvitationForm", {
            identifying: true,
            inverse: "selectablePartnerViews",
        }),
        partner: one("Partner", {
            identifying: true,
            inverse: "channelInvitationFormSelectablePartnerViews",
        }),
        personaImStatusIconView: one("PersonaImStatusIconView", {
            inverse: "channelInvitationFormSelectablePartnerViewOwner",
            compute() {
                return this.partner.isImStatusSet ? {} : clear();
            },
        }),
    },
});
