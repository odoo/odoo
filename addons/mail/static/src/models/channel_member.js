/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMember',
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
        callParticipantCards: many('CallParticipantCard', {
            inverse: 'channelMember',
            isCausal: true,
        }),
        channel: one('Channel', {
            inverse: 'channelMembers',
            readonly: true,
            required: true,
        }),
        channelAsMemberOfCurrentUser: one('Channel', {
            compute() {
                return this.isMemberOfCurrentUser ? this.channel : clear();
            },
            inverse: 'memberOfCurrentUser',
        }),
        channelAsOfflineMember: one('Channel', {
            compute() {
                if (this.persona.partner) {
                    return !this.persona.partner.isOnline ? this.channel : clear();
                }
                if (this.persona.guest) {
                    return !this.persona.guest.isOnline ? this.channel : clear();
                }
                return clear();
            },
            inverse: 'orderedOfflineMembers',
        }),
        channelAsOnlineMember: one('Channel', {
            compute() {
                if (this.persona.partner) {
                    return this.persona.partner.isOnline ? this.channel : clear();
                }
                if (this.persona.guest) {
                    return this.persona.guest.isOnline ? this.channel : clear();
                }
                return clear();
            },
            inverse: 'orderedOnlineMembers',
        }),
        channelMemberViews: many('ChannelMemberView', {
            inverse: 'channelMember',
        }),
        id: attr({
            identifying: true,
        }),
        isMemberOfCurrentUser: attr({
            compute() {
                if (this.messaging.currentPartner) {
                    return this.messaging.currentPartner.persona === this.persona;
                }
                if (this.messaging.currentGuest) {
                    return this.messaging.currentGuest.persona === this.persona;
                }
                return clear();
            },
            default: false,
        }),
        isStreaming: attr({
            compute() {
                return Boolean(this.rtcSession && this.rtcSession.videoStream);
            },
        }),
        isTyping: attr({
            default: false,
        }),
        otherMemberLongTypingInThreadTimers: many('OtherMemberLongTypingInThreadTimer', {
            inverse: 'member',
        }),
        persona: one('Persona', {
            inverse: 'channelMembers',
            readonly: true,
            required: true,
        }),
        rtcSession: one('RtcSession', {
            inverse: 'channelMember',
        }),
    },
});
