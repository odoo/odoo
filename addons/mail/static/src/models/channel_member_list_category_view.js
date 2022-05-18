/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

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
    },
});
