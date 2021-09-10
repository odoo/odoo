/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class MessageReactionGroupSummaryView extends dependencies['mail.model'] {
        /**
         * @override
         */
        _created() {
            super._created();
            this.onClickReaction = this.onClickReaction.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {Object} messageReactionGroup
         */
        onClickReaction(messageReactionGroup) {
            this.messageReactionsSummaryView.update({
                highlightedReaction: replace(messageReactionGroup)
            });
        }


    }

    MessageReactionGroupSummaryView.fields = {
        messageReactionGroup: many2one('mail.message_reaction_group', {
            inverse: 'messageReactionGroupSummaryViews',
            readonly: true,
        }),
        messageReactionsSummaryView: many2one('mail.message_reactions_summary_view', {
            inverse: 'messageReactionGroupSummaryViews',
        }),
    };
    MessageReactionGroupSummaryView.identifyingFields = ['messageReactionGroup'];
    MessageReactionGroupSummaryView.modelName = 'mail.message_reaction_group_summary_view';

    return MessageReactionGroupSummaryView;
}

registerNewModel('mail.message_reaction_group_summary_view', factory);
