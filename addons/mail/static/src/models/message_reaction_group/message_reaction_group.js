/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class MessageReactionGroup extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUserReacted() {
            return Boolean(
                (this.messaging.currentPartner && this.partners.includes(this.messaging.currentPartner)) ||
                (this.messaging.currentGuest && this.guests.includes(this.messaging.currentGuest))
            );
        }

        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessage() {
            return insertAndReplace({ id: this.messageId });
        }

        /**
         * @private
         * @returns {string}
         */
        _computeSummary() {
            const {
                length,
                0: firstUser,
                1: secondUser,
                2: thirdUser,
            } = [
                ...this.partners.map(partner => partner.nameOrDisplayName),
                ...this.guests.map(guest => guest.name),
            ];
            switch (length) {
                case 1:
                    return _.str.sprintf(this.env._t('%s has reacted with %s'), firstUser, this.content);
                case 2:
                    return _.str.sprintf(this.env._t('%s and %s have reacted with %s'), firstUser, secondUser, this.content);
                case 3:
                    return _.str.sprintf(this.env._t('%s, %s, %s have reacted with %s'), firstUser, secondUser, thirdUser, this.content);
                case 4:
                    return _.str.sprintf(this.env._t('%s, %s, %s and 1 other person have reacted with %s'), firstUser, secondUser, thirdUser, this.content);
                default:
                    return _.str.sprintf(this.env._t('%s, %s, %s and %s other persons have reacted with %s'), firstUser, secondUser, thirdUser, length - 3, this.content);
            }
        }

    }

    MessageReactionGroup.fields = {
        content: attr({
            readonly: true,
            required: true,
        }),
        count: attr({
            required: true,
        }),
        /**
         * States the guests that have used this reaction on this message.
         */
        guests: many2many('mail.guest'),
        hasUserReacted: attr({
            compute: '_computeHasUserReacted',
            default: false,
        }),
        message: many2one('mail.message', {
            compute: '_computeMessage',
            inverse: 'messageReactionGroups',
            readonly: true,
            required: true,
        }),
        messageId: attr({
            readonly: true,
            required: true,
        }),
        messageReactionGroupViews: one2many('mail.message_reaction_group_view', {
            inverse: 'messageReactionGroup',
            isCausal: true,
        }),
        messageReactionGroupSummaryViews: one2many('mail.message_reaction_group_summary_view', {
            inverse: 'messageReactionGroup',
            isCausal: true,
        }),
        /**
         * States the partners that have used this reaction on this message.
         */
        partners: many2many('mail.partner'),
        summary: attr({
            compute: '_computeSummary',
        }),
    };
    MessageReactionGroup.identifyingFields = ['message', 'content'];
    MessageReactionGroup.modelName = 'mail.message_reaction_group';

    return MessageReactionGroup;
}

registerNewModel('mail.message_reaction_group', factory);
