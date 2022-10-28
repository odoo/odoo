/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one} from '@mail/model/model_field';

registerModel({
    name: 'MessageReactionGroupItem',
    recordMethods: {
        /**
         * Handles click on the reaction group Item in massage context dialog,
         *in order to set messageContextState in messageContextViewOwner.
         * @param {MouseEvent} ev
         */
        onClickReactionGroupItem(reactionGroup) {
            this.messageContextViewOwner.update({ messageContextState: reactionGroup });
        },
    },
    fields: {
        messageContextViewOwner: one('MessageContextMenu', {
            identifying: true,
            inverse: 'messageContextReactionItems',
        }),
        messageReactionGroup: one('MessageReactionGroup', {
            identifying: true,
            inverse: 'messageContextReactionItems'
        }),
        messageViewOwner: one('MessageView', {
            related : 'messageContextViewOwner.messageViewOwner'
        }),
    },
});
