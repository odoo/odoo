/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'Channel',
    identifyingFields: ['id'],
    recordMethods: {
        async fetchChannelMembers() {
            const channelData = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'load_more_members',
                args: [[this.id]],
                kwargs: {
                    known_member_ids: this.channelMembers.map(channelMember => channelMember.id),
                },
            });
            if (!this.exists()) {
                return;
            }
            this.update(channelData);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeAreAllMembersLoaded() {
            return this.memberCount === this.channelMembers.length;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            return insertAndReplace({
                id: this.id,
                model: 'mail.channel',
            });
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeUnknownMemberCount() {
            return this.memberCount - this.channelMembers.length;
        },
        /**
         * @private
         * @returns {Array[]}
         */
        _sortMembers() {
            return [
                ['truthy-first', 'name'],
                ['case-insensitive-asc', 'name'],
            ];
        },
    },
    fields: {
        areAllMembersLoaded: attr({
            compute: '_computeAreAllMembersLoaded',
        }),
        channelMembers: many('ChannelMember', {
            inverse: 'channel',
            isCausal: true,
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        memberCount: attr({
            related: 'thread.memberCount',
        }),
        orderedOfflineMembers: many('ChannelMember', {
            inverse: 'channelAsOfflineMember',
            sort: '_sortMembers',
        }),
        orderedOnlineMembers: many('ChannelMember', {
            inverse: 'channelAsOnlineMember',
            sort: '_sortMembers',
        }),
        thread: one('Thread', {
            compute: '_computeThread',
            inverse: 'channel',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        /**
         * States how many members are currently unknown on the client side.
         * This is the difference between the total number of members of the
         * channel as reported in memberCount and those actually in members.
         */
        unknownMemberCount: attr({
            compute: '_computeUnknownMemberCount',
        }),
    },
});
