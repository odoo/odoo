/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";

import { sprintf } from "@web/core/utils/strings";

Model({
    name: "ChannelMemberListCategoryView",
    template: "mail.ChannelMemberListCategoryView",
    identifyingMode: "xor",
    fields: {
        channel: one("Channel", {
            required: true,
            compute() {
                if (this.channelMemberListViewOwnerAsOffline) {
                    return this.channelMemberListViewOwnerAsOffline.channel;
                }
                if (this.channelMemberListViewOwnerAsOnline) {
                    return this.channelMemberListViewOwnerAsOnline.channel;
                }
            },
        }),
        channelMemberListViewOwnerAsOffline: one("ChannelMemberListView", {
            identifying: true,
            inverse: "offlineCategoryView",
        }),
        channelMemberListViewOwnerAsOnline: one("ChannelMemberListView", {
            identifying: true,
            inverse: "onlineCategoryView",
        }),
        channelMemberViews: many("ChannelMemberView", {
            inverse: "channelMemberListCategoryViewOwner",
            compute() {
                if (this.members.length === 0) {
                    return clear();
                }
                return this.members.map((channelMember) => ({ channelMember }));
            },
        }),
        members: many("ChannelMember", {
            compute() {
                if (this.channelMemberListViewOwnerAsOnline) {
                    return this.channel.orderedOnlineMembers;
                }
                if (this.channelMemberListViewOwnerAsOffline) {
                    return this.channel.orderedOfflineMembers;
                }
                return clear();
            },
        }),
        title: attr({
            compute() {
                let categoryText = "";
                if (this.channelMemberListViewOwnerAsOnline) {
                    categoryText = this.env._t("Online");
                }
                if (this.channelMemberListViewOwnerAsOffline) {
                    categoryText = this.env._t("Offline");
                }
                return sprintf(this.env._t("%(categoryText)s - %(memberCount)s"), {
                    categoryText,
                    memberCount: this.members.length,
                });
            },
        }),
    },
});
