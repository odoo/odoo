/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChannelMemberListView',
    identifyingFields: ['threadView'],
    fields: {
        threadView: one('ThreadView', {
            inverse: 'channelMemberListView',
            readonly: true,
            required: true,
        }),
    },
});
