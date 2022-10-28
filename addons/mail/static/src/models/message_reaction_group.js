/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'MessageReactionGroup',
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
            compute() {
                return Boolean(
                    (this.messaging.currentPartner && this.partners.includes(this.messaging.currentPartner)) ||
                    (this.messaging.currentGuest && this.guests.includes(this.messaging.currentGuest))
                );
            },
            default: false,
        }),
        message: one('Message', {
            identifying: true,
            inverse: 'messageReactionGroups',
        }),
        messageReactionGroupViews: many('MessageReactionGroupView', {
            inverse: 'messageReactionGroup',
        }),
        messageContextReactionItems: many('MessageReactionGroupItem', {
            inverse: 'messageReactionGroup',
        }),
        messageContextReactionPartners: many('MessageReactionGroupPartner', {
            inverse: 'messageReactionGroup',
        }),
        /**
         * States the partners that have used this reaction on this message.
         */
        partners: many('Partner'),
    },
});
