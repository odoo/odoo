/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one, attr } from '@mail/model/model_field';

registerModel({
    name: 'MessageContextMenu',
    fields: {
        messageContextPopoverView: one('PopoverView', {
            identifying: true,
            inverse: 'messageContextMenuView',
        }),
        messageView: one('MessageView', {
            related: 'messageContextPopoverView.messageViewOwnerAsContextMenu',
        }),
        component: attr(),
    }

});
