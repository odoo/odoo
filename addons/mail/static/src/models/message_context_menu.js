/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one, attr } from '@mail/model/model_field';

registerModel({
    name: 'MessageContextMenu',
    fields: {
        headerView: one('MessageContextHeaderView', {
            default: {},
            inverse: 'messageContextViewOwner',
            readonly: true,
            required: true,
        }),
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
