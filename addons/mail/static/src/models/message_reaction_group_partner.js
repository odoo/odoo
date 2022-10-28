/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MessageReactionGroupPartner',
    fields: {
        messageContextViewOwner: one('MessageContextMenu', {
            identifying: true,
            inverse: 'messageContextReactionPartners',
        }),
        messageReactionGroup: one('MessageReactionGroup', {
            identifying: true,
            inverse: 'messageContextReactionPartners'
        }),
        messageViewOwner: one('MessageView', {
            related : 'messageContextViewOwner.messageViewOwner'
        }),
    },
});
