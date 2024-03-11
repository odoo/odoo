/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'ChannelMemberListCategoryView',
    identifyingMode: 'xor',
    fields: {
        channel: one('Channel', {
            compute() {
                if (this.channelMemberListViewOwnerAsOffline) {
                    return this.channelMemberListViewOwnerAsOffline.channel;
                }
                if (this.channelMemberListViewOwnerAsOnline) {
                    return this.channelMemberListViewOwnerAsOnline.channel;
                }
            },
            required: true,
        }),
        channelMemberListViewOwnerAsOffline: one('ChannelMemberListView', {
            identifying: true,
            inverse: 'offlineCategoryView',
        }),
        channelMemberListViewOwnerAsOnline: one('ChannelMemberListView', {
            identifying: true,
            inverse: 'onlineCategoryView',
        }),
        channelMemberViews: many('ChannelMemberView', {
            compute() {
                if (this.members.length === 0) {
                    return clear();
                }
                return this.members.map(channelMember => ({ channelMember }));
            },
            inverse: 'channelMemberListCategoryViewOwner',
        }),
        members: many('ChannelMember', {
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
                return sprintf(
                    this.env._t("%(categoryText)s - %(memberCount)s"),
                    {
                        categoryText,
                        memberCount: this.members.length,
                    }
                );
            },
        }),
    },
});
