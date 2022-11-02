/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ChatWindowHiddenMenuItemView',
    template: 'mail.ChatWindowHiddenMenuItemView',
    templateGetter: 'chatWindowHiddenMenuItemView',
    fields: {
        chatWindowHeaderView: one('ChatWindowHeaderView', {
            identifying: true,
            inverse: 'hiddenMenuItem',
        }),
        isLast: attr({
            compute() {
                return this.owner.lastItem === this;
            },
            default: false,
        }),
        owner: one('ChatWindowHiddenMenuView', {
            identifying: true,
            inverse: 'items',
        }),
    },
});
