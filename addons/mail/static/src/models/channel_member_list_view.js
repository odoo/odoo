/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChannelMemberListView',
    identifyingFields: [['chatWindowOwner', 'threadViewOwner']],
    fields: {
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
