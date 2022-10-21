/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MessageContextHeaderView',
    fields: {
        messageContextViewOwner: one('MessageContextMenu', {
            identifying: true,
            inverse: 'headerView',
        }),
        mostEmojiUsedItems: one('MessageContextMostUsedImojiView', {
            default: {},
            inverse: 'MostUsedImojiViewOwner',
        }),
    },
});
