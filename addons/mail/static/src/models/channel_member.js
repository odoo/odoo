/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMember',
    recordMethods: {
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeAvatarUrl() {
            if (this.persona.partner) {
                return `/mail/channel/${this.channel.id}/partner/${this.persona.partner.id}/avatar_128`;
            }
            if (this.persona.guest) {
                return `/mail/channel/${this.channel.id}/guest/${this.persona.guest.id}/avatar_128?unique=${this.persona.guest.name}`;
            }
            return clear();
        },
        /**
         * @private
         * @returns {Object|FieldCommand}
         */
        _computeChannelAsMemberOfCurrentUser() {
            return this.isMemberOfCurrentUser ? this.channel : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannelAsOfflineMember() {
            if (this.persona.partner) {
                return !this.persona.partner.isOnline ? this.channel : clear();
            }
            if (this.persona.guest) {
                return !this.persona.guest.isOnline ? this.channel : clear();
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannelAsOnlineMember() {
            if (this.persona.partner) {
                return this.persona.partner.isOnline ? this.channel : clear();
            }
            if (this.persona.guest) {
                return this.persona.guest.isOnline ? this.channel : clear();
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsMemberOfCurrentUser() {
            if (this.messaging.currentPartner) {
                return this.messaging.currentPartner.persona === this.persona;
            }
            if (this.messaging.currentGuest) {
                return this.messaging.currentGuest.persona === this.persona;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsStreaming() {
            return Boolean(this.rtcSession && this.rtcSession.videoStream);
        },
    },
    fields: {
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
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
            compute: '_computeChannelAsMemberOfCurrentUser',
            inverse: 'memberOfCurrentUser',
        }),
        channelAsOfflineMember: one('Channel', {
            compute: '_computeChannelAsOfflineMember',
            inverse: 'orderedOfflineMembers',
        }),
        channelAsOnlineMember: one('Channel', {
            compute: '_computeChannelAsOnlineMember',
            inverse: 'orderedOnlineMembers',
        }),
        channelMemberViews: many('ChannelMemberView', {
            inverse: 'channelMember',
            isCausal: true,
        }),
        id: attr({
            identifying: true,
        }),
        isMemberOfCurrentUser: attr({
            compute: '_computeIsMemberOfCurrentUser',
            default: false,
        }),
        isStreaming: attr({
            compute: '_computeIsStreaming',
        }),
        isTyping: attr({
            default: false,
        }),
        otherMemberLongTypingInThreadTimers: many('OtherMemberLongTypingInThreadTimer', {
            inverse: 'member',
            isCausal: true,
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
