/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageReactionGroupView',
    identifyingFields: ['messageReactionGroup', 'messageView'],
    recordMethods: {
        /**
         * Handles click on the reaction group.
         *
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            markEventHandled(ev, 'messageReactionGroupView.Click');
            if (this.messageReactionGroup.hasUserReacted) {
                this.messageReactionGroup.message.removeReaction(this.messageReactionGroup.content);
            } else {
                this.messageReactionGroup.message.addReaction(this.messageReactionGroup.content);
            }
        },
        /**
         * Handles right click or long press touch in mobile on the reaction group.
         *
         * @param {MouseEvent} ev
         */
        onContextMenu(ev) {
            ev.preventDefault();
            markEventHandled(ev, 'messageReactionGroupView.onContextMenu');
            this.messageView.threadView.openReactionsSummary(this.messageReactionGroup);
        },
    },
    fields: {
        messageReactionGroup: one('MessageReactionGroup', {
            inverse: 'messageReactionGroupViews',
            readonly: true,
        }),
        messageView: one('MessageView', {
            inverse: 'messageReactionGroupViews',
            readonly: true,
        }),
    },
});
