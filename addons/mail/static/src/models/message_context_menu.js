/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one, attr } from '@mail/model/model_field';

registerModel({
    name: 'MessageContextMenu',
    fields: {
        reactionSummaryView: one('MessageContextReactionSummary', {
            default: {},
            inverse: 'messageContextViewOwner',
            readonly: true,
            required: true,
        }), 
        messageView: one('MessageView', {
        }),
    }

});
