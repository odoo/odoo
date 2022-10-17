/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChatWindowHiddenMenuView',
    fields: {
        owner: one('ChatWindowManager', {
            identifying: true,
            inverse: 'hiddenMenuView',
        }),
    },
});
