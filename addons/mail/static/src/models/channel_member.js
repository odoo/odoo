/** @odoo-module **/

import { attr, clear, one, many, Model } from "@mail/model";

Model({
    name: "ChannelMember",
    fields: {
        avatarUrl: attr({
            compute() {
                if (this.persona.partner) {
                    return `/mail/channel/${this.channel.id}/partner/${this.persona.partner.id}/avatar_128`;
                }
                if (this.persona.guest) {
                    return `/mail/channel/${this.channel.id}/guest/${this.persona.guest.id}/avatar_128?unique=${this.persona.guest.name}`;
                }
                return clear();
            },
        }),
        callParticipantCards: many("CallParticipantCard", {
            inverse: "channelMember",
            isCausal: true,
        }),
        channel: one("Channel", { inverse: "channelMembers", readonly: true, required: true }),
        channelAsMemberOfCurrentUser: one("Channel", {
            inverse: "memberOfCurrentUser",
            compute() {
                return this.isMemberOfCurrentUser ? this.channel : clear();
            },
        }),
        channelAsOfflineMember: one("Channel", {
            inverse: "orderedOfflineMembers",
            compute() {
                if (this.persona.partner) {
                    return !this.persona.partner.isOnline ? this.channel : clear();
                }
                if (this.persona.guest) {
                    return !this.persona.guest.isOnline ? this.channel : clear();
                }
                return clear();
            },
        }),
        channelAsOnlineMember: one("Channel", {
            inverse: "orderedOnlineMembers",
            compute() {
                if (this.persona.partner) {
                    return this.persona.partner.isOnline ? this.channel : clear();
                }
                if (this.persona.guest) {
                    return this.persona.guest.isOnline ? this.channel : clear();
                }
                return clear();
            },
        }),
        channelMemberViews: many("ChannelMemberView", { inverse: "channelMember" }),
        id: attr({ identifying: true }),
        isMemberOfCurrentUser: attr({
            default: false,
            compute() {
                if (this.messaging.currentPartner) {
                    return this.messaging.currentPartner.persona === this.persona;
                }
                if (this.messaging.currentGuest) {
                    return this.messaging.currentGuest.persona === this.persona;
                }
                return clear();
            },
        }),
        isStreaming: attr({
            compute() {
                return Boolean(this.rtcSession && this.rtcSession.videoStream);
            },
        }),
        isTyping: attr({ default: false }),
        otherMemberLongTypingInThreadTimers: many("OtherMemberLongTypingInThreadTimer", {
            inverse: "member",
        }),
        persona: one("Persona", { inverse: "channelMembers", readonly: true, required: true }),
        rtcSession: one("RtcSession", { inverse: "channelMember" }),
    },
});
