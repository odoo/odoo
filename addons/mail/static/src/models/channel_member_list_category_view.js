/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'ChannelMemberListCategoryView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannel() {
            if (this.channelMemberListViewOwnerAsOffline) {
                return this.channelMemberListViewOwnerAsOffline.channel;
            }
            if (this.channelMemberListViewOwnerAsOnline) {
                return this.channelMemberListViewOwnerAsOnline.channel;
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannelMemberViews() {
            if (this.members.length === 0) {
                return clear();
            }
            return insertAndReplace(
                this.members.map(channelMember => ({ channelMember })),
            );
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMembers() {
            if (!this.exists()) {
                return clear();
            }
            if (this.channelMemberListViewOwnerAsOnline) {
                return this.channel.orderedOnlineMembers;
            }
            if (this.channelMemberListViewOwnerAsOffline) {
                return this.channel.orderedOfflineMembers;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeTitle() {
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
    },
    fields: {
        channel: one('Channel', {
            compute: '_computeChannel',
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
            compute: '_computeChannelMemberViews',
            inverse: 'channelMemberListCategoryViewOwner',
            isCausal: true,
        }),
        members: many('ChannelMember', {
            compute: '_computeMembers',
        }),
        title: attr({
            compute: '_computeTitle',
        }),
    },
});
