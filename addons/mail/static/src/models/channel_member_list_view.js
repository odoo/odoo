/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMemberListView',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            this.channel.fetchChannelMembers();
        },
    },
    recordMethods: {
        /**
         * Handles click on the "load more members" button.
         */
        async onClickLoadMoreMembers() {
            this.channel.fetchChannelMembers();
        },
    },
    fields: {
        channel: one('Channel', {
            compute() {
                if (this.chatWindowOwner) {
                    return this.chatWindowOwner.thread.channel;
                }
                if (this.threadViewOwner) {
                    return this.threadViewOwner.thread.channel;
                }
                return clear();
            },
        }),
        chatWindowOwner: one('ChatWindow', {
            identifying: true,
            inverse: 'channelMemberListView',
        }),
        offlineCategoryView: one('ChannelMemberListCategoryView', {
            compute() {
                if (this.channel && this.channel.orderedOfflineMembers.length > 0) {
                    return {};
                }
                return clear();
            },
            inverse: 'channelMemberListViewOwnerAsOffline',
        }),
        onlineCategoryView: one('ChannelMemberListCategoryView', {
            compute() {
                if (this.channel && this.channel.orderedOnlineMembers.length > 0) {
                    return {};
                }
                return clear();
            },
            inverse: 'channelMemberListViewOwnerAsOnline',
        }),
        threadViewOwner: one('ThreadView', {
            identifying: true,
            inverse: 'channelMemberListView',
        }),
    },
});
