/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ChatWindowHiddenMenuView',
    fields: {
        component: attr(),
        owner: one('ChatWindowManager', {
            identifying: true,
            inverse: 'hiddenMenuView',
        }),
    },
});
