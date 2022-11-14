/** @odoo-module **/

import { clear, one, Model } from "@mail/model";

Model({
    name: "ChannelMemberListView",
    template: "mail.ChannelMemberListView",
    identifyingMode: "xor",
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
        channel: one("Channel", {
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
        chatWindowOwner: one("ChatWindow", { identifying: true, inverse: "channelMemberListView" }),
        offlineCategoryView: one("ChannelMemberListCategoryView", {
            inverse: "channelMemberListViewOwnerAsOffline",
            compute() {
                if (this.channel && this.channel.orderedOfflineMembers.length > 0) {
                    return {};
                }
                return clear();
            },
        }),
        onlineCategoryView: one("ChannelMemberListCategoryView", {
            inverse: "channelMemberListViewOwnerAsOnline",
            compute() {
                if (this.channel && this.channel.orderedOnlineMembers.length > 0) {
                    return {};
                }
                return clear();
            },
        }),
        threadViewOwner: one("ThreadView", { identifying: true, inverse: "channelMemberListView" }),
    },
});
