/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

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
        _computeCallParticipants() {
            const callParticipants = this.thread.invitedMembers;
            for (const rtcSession of this.thread.rtcSessions) {
                callParticipants.push(rtcSession.channelMember);
            }
            return replace(callParticipants);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeCorrespondent() {
            if (this.channel_type === 'channel') {
                return clear();
            }
            const correspondents = this.thread.members.filter(partner =>
                partner !== this.messaging.currentPartner
            );
            if (correspondents.length === 1) {
                // 2 members chat
                return replace(correspondents[0]);
            }
            if (this.thread.members.length === 1) {
                // chat with oneself
                return replace(this.thread.members[0]);
            }
            return clear();
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
        _sortCallParticipants() {
            return [
                ['truthy-first', 'rtcSession'],
                ['smaller-first', 'rtcSession.id'],
            ];
        },
        /**
         * @private
         * @returns {Array[]}
         */
        _sortMembers() {
            return [
                ['truthy-first', 'persona.name'],
                ['case-insensitive-asc', 'persona.name'],
            ];
        },
    },
    fields: {
        areAllMembersLoaded: attr({
            compute: '_computeAreAllMembersLoaded',
        }),
        /**
         * Cache key to force a reload of the avatar when avatar is changed.
         */
        avatarCacheKey: attr(),
        callParticipants: many('ChannelMember', {
            compute: '_computeCallParticipants',
            sort: '_sortCallParticipants',
        }),
        channelMembers: many('ChannelMember', {
            inverse: 'channel',
            isCausal: true,
        }),
        /**
         * Either 'channel', 'chat', 'group', or 'livechat'.
         */
        channel_type: attr(),
        correspondent: one('Partner', {
            compute: '_computeCorrespondent',
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
