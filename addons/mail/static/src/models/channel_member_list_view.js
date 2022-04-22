/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMemberListView',
    identifyingFields: [['chatWindowOwner', 'threadViewOwner']],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannel() {
            if (this.chatWindowOwner) {
                return replace(this.chatWindowOwner.thread);
            }
            if (this.threadViewOwner) {
                return replace(this.threadViewOwner.thread);
            }
            return clear();
        },
    },
    fields: {
        channel: one('Thread', {
            compute: '_computeChannel',
            readonly: true,
        }),
        chatWindowOwner: one('ChatWindow', {
            inverse: 'channelMemberListView',
            readonly: true,
        }),
        threadViewOwner: one('ThreadView', {
            inverse: 'channelMemberListView',
            readonly: true,
        }),
    },
});
