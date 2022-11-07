/** @odoo-module **/

import { one, Model } from '@mail/model';


Model({
    name: 'MessageReactionGroupItem',
    template: 'mail.MessageReactionGroupItem',
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
