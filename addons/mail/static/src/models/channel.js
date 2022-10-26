/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Channel',
    modelMethods: {
        /**
         * Performs the `channel_get` RPC on `mail.channel`.
         *
         * `openChat` is preferable in business code because it will avoid the
         * RPC if the chat already exists.
         *
         * @param {Object} param0
         * @param {integer[]} param0.partnerIds
         * @param {boolean} [param0.pinForCurrentPartner]
         * @returns {Channel|undefined} the created or existing chat
         */
        async performRpcCreateChat({ partnerIds, pinForCurrentPartner }) {
            // TODO FIX: potential duplicate chat task-2276490
            const data = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_get',
                kwargs: {
                    partners_to: partnerIds,
                    pin: pinForCurrentPartner,
                },
            });
            if (!data) {
                return;
            }
            const { channel } = this.messaging.models['Thread'].insert(
                this.messaging.models['Thread'].convertData(data)
            );
            return channel;
        },
    },
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
    },
    fields: {
        activeRtcSession: one('RtcSession'),
        areAllMembersLoaded: attr({
            compute() {
                return this.memberCount === this.channelMembers.length;
            },
        }),
        /**
         * Cache key to force a reload of the avatar when avatar is changed.
         */
        avatarCacheKey: attr(),
        callParticipants: many('ChannelMember', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                const callParticipants = this.thread.invitedMembers;
                for (const rtcSession of this.thread.rtcSessions) {
                    callParticipants.push(rtcSession.channelMember);
                }
                return callParticipants;
            },
            sort: [
                ['truthy-first', 'rtcSession'],
                ['smaller-first', 'rtcSession.id'],
            ],
        }),
        channelMembers: many('ChannelMember', {
            inverse: 'channel',
            isCausal: true,
        }),
        channelPreviewViews: many('ChannelPreviewView', {
            inverse: 'channel',
        }),
        channel_type: attr(),
        correspondent: one('Partner', {
            compute() {
                if (this.channel_type === 'channel') {
                    return clear();
                }
                const correspondents = this.channelMembers
                    .filter(member => member.persona && member.persona.partner && !member.isMemberOfCurrentUser)
                    .map(member => member.persona.partner);
                if (correspondents.length === 1) {
                    // 2 members chat
                    return correspondents[0];
                }
                const partners = this.channelMembers
                    .filter(member => member.persona && member.persona.partner)
                    .map(member => member.persona.partner);
                if (partners.length === 1) {
                    // chat with oneself
                    return partners[0];
                }
                return clear();
            },
        }),
        correspondentOfDmChat: one('Partner', {
            compute() {
                if (
                    this.channel_type === 'chat' &&
                    this.correspondent
                ) {
                    return this.correspondent;
                }
                return clear();
            },
            inverse: 'dmChatWithCurrentPartner',
        }),
        custom_channel_name: attr(),
        /**
         * Useful to compute `discussSidebarCategoryItem`.
         */
        discussSidebarCategory: one('DiscussSidebarCategory', {
            compute() {
                switch (this.channel_type) {
                    case 'channel':
                        return this.messaging.discuss.categoryChannel;
                    case 'chat':
                    case 'group':
                        return this.messaging.discuss.categoryChat;
                    default:
                        return clear();
                }
            },
        }),
        /**
         * Determines the discuss sidebar category item that displays this
         * channel.
         */
        discussSidebarCategoryItem: one('DiscussSidebarCategoryItem', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                if (!this.thread.isPinned) {
                    return clear();
                }
                if (!this.discussSidebarCategory) {
                    return clear();
                }
                return { category: this.discussSidebarCategory };
            },
            inverse: 'channel',
        }),
        displayName: attr({
            compute() {
                if (!this.thread) {
                    return;
                }
                if (this.channel_type === 'chat' && this.correspondent) {
                    return this.custom_channel_name || this.thread.getMemberName(this.correspondent.persona);
                }
                if (this.channel_type === 'group' && !this.thread.name) {
                    return this.channelMembers
                        .filter(channelMember => channelMember.persona)
                        .map(channelMember => this.thread.getMemberName(channelMember.persona))
                        .join(this.env._t(", "));
                }
                return this.thread.name;
            },
        }),
        id: attr({
            identifying: true,
        }),
        /**
         * Local value of message unread counter, that means it is based on
         * initial server value and updated with interface updates.
         */
        localMessageUnreadCounter: attr({
            compute() {
                if (!this.thread) {
                    return clear();
                }
                // By default trust the server up to the last message it used
                // because it's not possible to do better.
                let baseCounter = this.serverMessageUnreadCounter;
                let countFromId = this.thread.serverLastMessage ? this.thread.serverLastMessage.id : 0;
                // But if the client knows the last seen message that the server
                // returned (and by assumption all the messages that come after),
                // the counter can be computed fully locally, ignoring potentially
                // obsolete values from the server.
                const firstMessage = this.thread.orderedMessages[0];
                if (
                    firstMessage &&
                    this.thread.lastSeenByCurrentPartnerMessageId &&
                    this.thread.lastSeenByCurrentPartnerMessageId >= firstMessage.id
                ) {
                    baseCounter = 0;
                    countFromId = this.thread.lastSeenByCurrentPartnerMessageId;
                }
                // Include all the messages that are known locally but the server
                // didn't take into account.
                return this.thread.orderedMessages.reduce((total, message) => {
                    if (message.id <= countFromId) {
                        return total;
                    }
                    return total + 1;
                }, baseCounter);
            },
        }),
        /**
         * States the number of members in this channel according to the server.
         */
        memberCount: attr(),
        memberOfCurrentUser: one('ChannelMember', {
            inverse: 'channelAsMemberOfCurrentUser',
        }),
        orderedOfflineMembers: many('ChannelMember', {
            inverse: 'channelAsOfflineMember',
            sort: [
                ['truthy-first', 'persona.name'],
                ['case-insensitive-asc', 'persona.name'],
            ],
        }),
        orderedOnlineMembers: many('ChannelMember', {
            inverse: 'channelAsOnlineMember',
            sort: [
                ['truthy-first', 'persona.name'],
                ['case-insensitive-asc', 'persona.name'],
            ],
        }),
        /**
         * Message unread counter coming from server.
         *
         * Value of this field is unreliable, due to dynamic nature of
         * messaging. So likely outdated/unsync with server. Should use
         * localMessageUnreadCounter instead, which smartly guess the actual
         * message unread counter at all time.
         *
         * @see localMessageUnreadCounter
         */
        serverMessageUnreadCounter: attr({
            default: 0,
        }),
        /**
         * Determines whether we only display the participants who broadcast a video or all of them.
         */
        showOnlyVideo: attr({
            default: false,
        }),
        thread: one('Thread', {
            compute() {
                return {
                    id: this.id,
                    model: 'mail.channel',
                };
            },
            inverse: 'channel',
            isCausal: true,
            required: true,
        }),
        /**
         * States how many members are currently unknown on the client side.
         * This is the difference between the total number of members of the
         * channel as reported in memberCount and those actually in members.
         */
        unknownMemberCount: attr({
            compute() {
                return this.memberCount - this.channelMembers.length;
            },
        }),
    },
});
