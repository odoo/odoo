/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class MessageReactionGroupView extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            this.onClick = this.onClick.bind(this);
            this.onContextMenu = this.onContextMenu.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

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
        }

        /**
         * Handles right click or long press touch in mobile on the reaction group.
         *
         * @param {MouseEvent} ev
         */
        onContextMenu(ev) {
            markEventHandled(ev, 'messageReactionGroupView.onContextMenu');
            this.messageView.threadView.openReactionsSummary(this.messageReactionGroup);
        }

    }

    MessageReactionGroupView.fields = {
        messageReactionGroup: many2one('mail.message_reaction_group', {
            inverse: 'messageReactionGroupViews',
            readonly: true,
        }),
        messageView: many2one('mail.message_view', {
            inverse: 'messageReactionGroupViews',
            readonly: true,
        }),
    };
    MessageReactionGroupView.identifyingFields = ['messageReactionGroup', 'messageView'];
    MessageReactionGroupView.modelName = 'mail.message_reaction_group_view';

    return MessageReactionGroupView;
}

registerNewModel('mail.message_reaction_group_view', factory);
