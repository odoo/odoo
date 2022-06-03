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
         * @returns {FieldCommand}
         */
        _computeChannelAsOfflineMember() {
            return this.member && !this.member.isOnline ? replace(this.channel) : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannelAsOnlineMember() {
            return this.member && this.member.isOnline ? replace(this.channel) : clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeMember() {
            return this.partner ? this.partner : this.guest;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            return this.partner ? this.partner.nameOrDisplayName : this.guest.name;
        },
    },
    fields: {
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
        guest: one('Guest', {
            inverse: 'channelMembers',
            readonly: true,
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        name: attr({
            compute: '_computeName',
        }),
        member: attr({
            compute: '_computeMember',
        }),
        partner: one('Partner', {
            inverse: 'channelMembers',
            readonly: true,
        }),
    },
});
