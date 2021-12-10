/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageReactionGroupSummaryView',
    identifyingFields: ['messageReactionGroup', 'messageReactionsSummaryView'],
    recordMethods: {
        /**
         * @param {MessageReactionGroup} messageReactionGroup
         */
        onClickReaction(messageReactionGroup) {
            this.messageReactionsSummaryView.update({
                highlightedReaction: replace(messageReactionGroup)
            });
        },
    },
    fields: {
        messageReactionGroup: one('MessageReactionGroup', {
            inverse: 'messageReactionGroupSummaryViews',
            readonly: true,
        }),
        messageReactionsSummaryView: one('MessageReactionsSummaryView', {
            inverse: 'messageReactionGroupSummaryViews',
            readonly: true,
        }),
    },
});
