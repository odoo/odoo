/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChannelMemberView',
    identifyingFields: ['channelMemberListCategoryViewOwner', 'partner'],
    fields: {
        channelMemberListCategoryViewOwner: one('ChannelMemberListCategoryView', {
            inverse: 'channelMemberViews',
            readonly: true,
            required: true,
        }),
        partner: one('Partner', {
            inverse: 'channelMemberViews',
            readonly: true,
            required: true,
        }),
    },
});
