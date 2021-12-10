/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace, unlink } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageReactionsSummaryView',
    identifyingFields: ['threadView'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeGuestsWhoReacted() {
            if (this.highlightedReaction) {
                return replace(this.highlightedReaction.guests);
            }
            else {
                return clear();
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeHighlightedReaction() {
            if (!this.highlightedReaction) {
                if(this.message.messageReactionGroups.length > 0) {
                    return replace(this.message.messageReactionGroups[0]);
                }
                if(this.messageReactionGroupSummaryViews.length > 0) {
                    return replace(this.messageReactionGroupSummaryViews[0].messageReactionGroup);
                }
                return clear();
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageReactionGroupSummaryViews() {
            if (!this.highlightedReaction) {
                return clear();
            }
            const messageReactionGroupSummaryViewsData = [];
            for (const reaction of this.highlightedReaction.message.messageReactionGroups) {
                messageReactionGroupSummaryViewsData.push({
                    messageReactionGroup: replace(reaction),
                });
            }
            return insertAndReplace(messageReactionGroupSummaryViewsData);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePartnersWhoReacted() {
            if (this.highlightedReaction) {
                return replace(this.highlightedReaction.partners);
            }
            else {
                return clear();
            }
        },
    },
    fields: {
        /**
         * States the OWL component of this message reactions summary.
         */
        component: attr(),
        guests: many('Guest', {
            compute: '_computeGuestsWhoReacted',
        }),
        highlightedReaction: one('MessageReactionGroup', {
            compute: '_computeHighlightedReaction',
        }),
        message: one('Message', {
            inverse: 'messageReactionsSummaryViews',
            readonly: true,
        }),
        messageReactionGroupSummaryViews: many('MessageReactionGroupSummaryView', {
            compute: '_computeMessageReactionGroupSummaryViews',
            inverse: 'messageReactionsSummaryView',
            isCausal: true,
        }),
        partners: many('Partner', {
            compute: '_computePartnersWhoReacted',
        }),
        threadView: one('ThreadView', {
            inverse: 'messageReactionsSummaryView',
            readonly: true,
        }),
    },
});
