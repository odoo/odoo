/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2one, one2many } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace, unlink } from '@mail/model/model_field_command';

function factory(dependencies) {

    class MessageReactionsSummaryView extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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
        }

        _computeGuestsWhoReacted() {
            if (this.highlightedReaction) {
                return replace(this.highlightedReaction.guests);
            }
            else {
                return clear();
            }
        }

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
        }

        _computePartnersWhoReacted() {
            if (this.highlightedReaction) {
                return replace(this.highlightedReaction.partners);
            }
            else {
                return clear();
            }
        }

    }

    MessageReactionsSummaryView.fields = {
        /**
         * States the OWL component of this message reactions summary.
         */
        component: attr(),
        guests: many2many('mail.guest', {
            compute: '_computeGuestsWhoReacted',
        }),
        highlightedReaction: many2one('mail.message_reaction_group', {
            compute: '_computeHighlightedReaction',
        }),
        message: many2one('mail.message', {
            inverse: 'messageReactionsSummaryViews',
            readonly: true,
        }),
        messageReactionGroupSummaryViews: one2many('mail.message_reaction_group_summary_view', {
            compute: '_computeMessageReactionGroupSummaryViews',
            inverse: 'messageReactionsSummaryView',
            isCausal: true,
        }),
        partners: many2many('mail.partner', {
            compute: '_computePartnersWhoReacted',
        }),
        threadView: one2one('mail.thread_view', {
            inverse: 'messageReactionsSummaryView',
            readonly: true,
        }),
    };

    MessageReactionsSummaryView.identifyingFields = ['threadView'];
    MessageReactionsSummaryView.modelName = 'mail.message_reactions_summary_view';

    return MessageReactionsSummaryView;
}

registerNewModel('mail.message_reactions_summary_view', factory);
