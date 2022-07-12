/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMember',
    identifyingFields: ['id'],
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
         * @returns {FieldCommand}
         */
        _computeChannelAsOfflineMember() {
            if (this.persona.partner) {
                return !this.persona.partner.isOnline ? replace(this.channel) : clear();
            }
            if (this.persona.guest) {
                return replace(this.channel);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannelAsOnlineMember() {
            if (this.persona.partner) {
                return this.persona.partner.isOnline ? replace(this.channel) : clear();
            }
            if (this.persona.guest) {
                return clear();
            }
            return clear();
        },
    },
    fields: {
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        channel: one('Channel', {
            inverse: 'channelMembers',
            readonly: true,
            required: true,
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
            readonly: true,
            required: true,
        }),
        persona: one('Persona', {
            inverse: 'channelMembers',
            readonly: true,
            required: true,
        }),
    },
});
