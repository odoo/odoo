/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { markEventHandled } from '@mail/utils/utils';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'MessageReactionGroup',
    recordMethods: {
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
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUserReacted() {
            return Boolean(
                (this.messaging.currentPartner && this.partners.includes(this.messaging.currentPartner)) ||
                (this.messaging.currentGuest && this.guests.includes(this.messaging.currentGuest))
            );
        },
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
                    return sprintf(this.env._t('%s has reacted with %s'), firstUser, this.content);
                case 2:
                    return sprintf(this.env._t('%s and %s have reacted with %s'), firstUser, secondUser, this.content);
                case 3:
                    return sprintf(this.env._t('%s, %s, %s have reacted with %s'), firstUser, secondUser, thirdUser, this.content);
                case 4:
                    return sprintf(this.env._t('%s, %s, %s and 1 other person have reacted with %s'), firstUser, secondUser, thirdUser, this.content);
                default:
                    return sprintf(this.env._t('%s, %s, %s and %s other persons have reacted with %s'), firstUser, secondUser, thirdUser, length - 3, this.content);
            }
        },
    },
    fields: {
        content: attr({
            identifying: true,
        }),
        count: attr({
            required: true,
        }),
        /**
         * States the guests that have used this reaction on this message.
         */
        guests: many('Guest'),
        hasUserReacted: attr({
            compute: '_computeHasUserReacted',
            default: false,
        }),
        message: one('Message', {
            identifying: true,
            inverse: 'messageReactionGroups',
        }),
        /**
         * States the partners that have used this reaction on this message.
         */
        partners: many('Partner'),
        summary: attr({
            compute: '_computeSummary',
        }),
    },
});
