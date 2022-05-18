/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMemberListCategoryView',
    identifyingFields: [['channelMemberListViewOwnerAsOffline', 'channelMemberListViewOwnerAsOnline']],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannel() {
            if (this.channelMemberListViewOwnerAsOffline) {
                return replace(this.channelMemberListViewOwnerAsOffline.channel);
            }
            if (this.channelMemberListViewOwnerAsOnline) {
                return replace(this.channelMemberListViewOwnerAsOnline.channel);
            }
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
                return replace(this.channel.orderedOnlineMembers);
            }
            if (this.channelMemberListViewOwnerAsOffline) {
                return replace(this.channel.orderedOfflineMembers);
            }
            return clear();
        },
    },
    fields: {
        channel: one('Thread', {
            compute: '_computeChannel',
            required: true,
        }),
        channelMemberListViewOwnerAsOffline: one('ChannelMemberListView', {
            inverse: 'offlineCategoryView',
            readonly: true,
        }),
        channelMemberListViewOwnerAsOnline: one('ChannelMemberListView', {
            inverse: 'onlineCategoryView',
            readonly: true,
        }),
        members: many('Partner', {
            compute: '_computeMembers',
        }),
    },
});
