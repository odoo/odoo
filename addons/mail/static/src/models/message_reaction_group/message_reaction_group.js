/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class MessageReactionGroup extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            this.onClick = this.onClick.bind(this);
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
            markEventHandled(ev, 'MessageReactionGroup.Click');
            if (this.hasUserReacted) {
                this.message.removeReaction(this.content);
            } else {
                this.message.addReaction(this.content);
            }
        }

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
                ...this.partners.map(partner => {
                    if (this.message.originThread) {
                        return this.message.originThread.getMemberName(partner);
                    }
                    return partner.nameOrDisplayName;
                }),
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
