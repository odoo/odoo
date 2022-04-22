/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChatWindowHeaderView',
    identifyingFields: ['chatWindowOwner'],
    fields: {
        chatWindowOwner: one('ChatWindow', {
            inverse: 'chatWindowHeaderView',
            readonly: true,
            required: true,
        }),
    },
});
