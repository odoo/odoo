/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'Channel',
    identifyingFields: ['id'],
    modelMethods: {
        /**
         * Performs the `channel_pin` RPC on `mail.channel`.
         *
         * @param {Object} param0
         * @param {number} param0.channelId
         * @param {boolean} [param0.pinned=false]
         */
        async performRpcChannelPin({ channelId, pinned = false }) {
            return this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_pin',
                args: [[channelId]],
                kwargs: {
                    pinned,
                },
            }, { shadow: true });
        },
    },
    recordMethods: {
        /**
         * Sets description of the channel to the given value.
         *
         * @param {string} description
         */
        async changeDescription(description) {
            this.update({ description });
            return this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_change_description',
                args: [[this.id]],
                kwargs: { description },
            });
        },
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
         * Notify server to leave the current channel. Useful for cross-tab and
         * cross-device chat window state synchronization.
         *
         * Only makes sense if isPendingPinned is set to the desired value.
         */
        async notifyPinStateToServer() {
            if (this.channel_type === 'channel') {
                await this.thread.leave();
                return;
            }
            await this.messaging.models['Channel'].performRpcChannelPin({
                channelId: this.id,
                pinned: this.isPendingPinned,
            });
        },
        /**
         * Pin this channel and notify server of the change.
         */
        async pin() {
            this.update({ isPendingPinned: true });
            if (this.messaging.currentUser) {
                await this.notifyPinStateToServer();
            }
        },
        /**
         * Unpin this thread and notify server of the change.
         */
        async unpin() {
            this.update({ isPendingPinned: false });
            if (this.messaging.currentUser) {
                await this.notifyPinStateToServer();
            }
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
        _computeCorrespondentOfDmChat() {
            if (
                this.channel_type === 'chat' &&
                this.correspondent &&
                this.public === 'private'
            ) {
                return replace(this.correspondent);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeDiscussSidebarCategoryItem() {
            if (!this.isPinned) {
                return clear();
            }
            if (!this.messaging.discuss) {
                return clear();
            }
            const discussSidebarCategory = this._getDiscussSidebarCategory();
            if (!discussSidebarCategory) {
                return clear();
            }
            return insertAndReplace({ category: replace(discussSidebarCategory) });
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasCallFeature() {
            const typesOfChannelWithCallFeature = new Set([
                'channel',
                'chat',
                'group',
            ]);
            return typesOfChannelWithCallFeature.has(this.channel_type);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasMemberListFeature() {
            const typesOfChannelWithMemberListFeature = new Set([
                'channel',
                'group',
            ]);
            return typesOfChannelWithMemberListFeature.has(this.channel_type);
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeInvitationLink() {
            if (!this.uuid || !this.channel_type || this.channel_type === 'chat') {
                return clear();
            }
            return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChat() {
            return this.channel_type === 'chat' || this.channel_type === 'group';
        },
        /**
        * @private
        * @returns {boolean}
        */
        _computeIsDescriptionEditable() {
            const typesOfChannelWithEditableDescription = new Set([
                'channel',
                'group',
            ]);
            return typesOfChannelWithEditableDescription.has(this.channel_type);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsDescriptionEditableByCurrentUser() {
            if (!this.messaging.currentUser || !this.messaging.currentUser.isInternalUser) {
                return false;
            }
            return this.isDescriptionEditable;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsPinned() {
            if (this.isPendingPinned) {
                return this.isPendingPinned;
            }
            return this.isServerPinned;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsRenamable() {
            const typesOfRenamableChannel = new Set([
                'channel',
                'chat',
                'group',
            ]);
            return typesOfRenamableChannel.has(this.channel_type);
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
         * Returns the discuss sidebar category that corresponds to this channel
         * type.
         *
         * @private
         * @returns {DiscussSidebarCategory}
         */
        _getDiscussSidebarCategory() {
            switch (this.channel_type) {
                case 'channel':
                    return this.messaging.discuss.categoryChannel;
                case 'chat':
                case 'group':
                    return this.messaging.discuss.categoryChat;
            }
        },
        /**
         * Handles change of pinned state coming from the server. Useful to
         * clear pending state once server acknowledged the change.
         *
         * @private
         * @see isPendingPinned
         */
        _onIsServerPinnedChanged() {
            if (this.isServerPinned === this.isPendingPinned) {
                this.update({ isPendingPinned: clear() });
            }
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
        authorizedGroupFullName: attr(),
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
        correspondentOfDmChat: one('Partner', {
            compute: '_computeCorrespondentOfDmChat',
            inverse: 'dmChatWithCurrentPartner',
        }),
        /**
         * Determines the default display mode of this channel. Should contain
         * either no value (to display the chat), or 'video_full_screen' to
         * start a call in full screen.
         */
        defaultDisplayMode: attr(),
        description: attr(),
        /**
         * Determines the discuss sidebar category item that displays this
         * channel.
         */
        discussSidebarCategoryItem: one('DiscussSidebarCategoryItem', {
            compute: '_computeDiscussSidebarCategoryItem',
            inverse: 'channel',
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines whether the RTC call feature should be displayed.
         */
        hasCallFeature: attr({
            compute: '_computeHasCallFeature',
        }),
        /**
         * Determines whether it makes sense for this channel to have a member
         * list.
         */
        hasMemberListFeature: attr({
            compute: '_computeHasMemberListFeature',
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        invitationLink: attr({
            compute: '_computeInvitationLink',
        }),
        /**
         * States whether this channel is qualified as chat.
         *
         * Useful to list chat channels, like in messaging menu with the filter
         * 'chat'.
         */
        isChat: attr({
            compute: '_computeIsChat',
        }),
        isDescriptionEditable: attr({
            compute: '_computeIsDescriptionEditable',
        }),
        isDescriptionEditableByCurrentUser: attr({
            compute: '_computeIsDescriptionEditableByCurrentUser',
        }),
        /**
         * Determines if there is a pending pin state change, which is a change
         * of pin state requested by the client but not yet confirmed by the
         * server.
         *
         * This field can be updated to immediately change the pin state on the
         * interface and to notify the server of the new state.
         */
        isPendingPinned: attr(),
        /**
         * Determines whether this channel is pinned in Discuss and present in
         * the messaging menu.
         */
        isPinned: attr({
            compute: '_computeIsPinned',
        }),
        isRenamable: attr({
            compute: '_computeIsRenamable',
            default: false,
        }),
        /**
         * Determines the last pin state known by the server, which is the pin
         * state displayed after initialization or when the last pending
         * pin state change was confirmed by the server.
         *
         * This field should be considered read only in most situations. Only
         * the code handling pin state change from the server should typically
         * update it.
         */
        isServerPinned: attr({
            default: false,
        }),
        /**
         * States the number of members in this channel according to the server.
         */
        memberCount: attr(),
        orderedOfflineMembers: many('ChannelMember', {
            inverse: 'channelAsOfflineMember',
            sort: '_sortMembers',
        }),
        orderedOnlineMembers: many('ChannelMember', {
            inverse: 'channelAsOnlineMember',
            sort: '_sortMembers',
        }),
        public: attr(),
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
        uuid: attr(),
    },
    onChanges: [
        new OnChange({
            dependencies: ['isServerPinned'],
            methodName: '_onIsServerPinnedChanged',
        }),
    ],
});
