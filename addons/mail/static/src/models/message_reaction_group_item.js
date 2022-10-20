/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one} from '@mail/model/model_field';

registerModel({
    name: 'MessageReactionGroupItem',
    template: 'mail.MessageReactionGroupItem',
    templateGetter: 'messageReactionGroupItem',
    recordMethods: {
        onClick() {
            if (!this.exists()) {
                return;
             }
            this.messageContextViewOwner.update({ reactionSelection: this.messageReactionGroup });
        },
    },
    fields: {
        messageContextViewOwner: one('MessageContextMenu', { identifying: true, inverse: 'items' }),
        messageReactionGroup: one('MessageReactionGroup', { identifying: true, inverse: 'messageContextReactionItems' }),
    },
});
