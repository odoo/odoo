/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MessageContextReactionSummary',
    fields: {
        messageContextViewOwner: one('MessageContextMenu', {
            identifying: true,
            inverse: 'reactionSummaryView',
        }),
    },
});
