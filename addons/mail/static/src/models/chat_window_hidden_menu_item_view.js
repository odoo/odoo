/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChatWindowHiddenMenuItemView',
    fields: {
        chatWindowHeaderView: one('ChatWindowHeaderView', {
            identifying: true,
            inverse: 'hiddenMenuItem',
        }),
        owner: one('ChatWindowHiddenMenuView', {
            identifying: true,
            inverse: 'items',
        }),
    },
});
