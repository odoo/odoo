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
            return this.partner && !this.partner.isOnline ? replace(this.channel) : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannelAsOnlineMember() {
            return this.partner && this.partner.isOnline ? replace(this.channel) : clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            if (!this.partner) {
                return;
            }
            return this.partner.nameOrDisplayName;
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
        id: attr({
            readonly: true,
            required: true,
        }),
        name: attr({
            compute: '_computeName',
        }),
        partner: one('Partner', {
            inverse: 'channelMembers',
            readonly: true,
        }),
    },
});
