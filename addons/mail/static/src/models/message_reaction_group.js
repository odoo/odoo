/** @odoo-module **/

import { attr, many, one, Model } from '@mail/model';

Model({
    name: 'MessageReactionGroup',
    fields: {
        content: attr({ identifying: true }),
        count: attr({ required: true }),
        /**
         * States the guests that have used this reaction on this message.
         */
        guests: many('Guest'),
        hasUserReacted: attr({ default: false,
            compute() {
                return Boolean(
                    (this.messaging.currentPartner && this.partners.includes(this.messaging.currentPartner)) ||
                    (this.messaging.currentGuest && this.guests.includes(this.messaging.currentGuest))
                );
            },
        }),
        message: one('Message', { identifying: true, inverse: 'messageReactionGroups' }),
        messageContextReactionItems: many('MessageReactionGroupItem', { inverse: 'messageReactionGroup' }),
        messageReactionGroupViews: many('MessageReactionGroupView', { inverse: 'messageReactionGroup' }),
        /**
         * States the partners that have used this reaction on this message.
         */
        partners: many('Partner'),
        personas: many('Persona', {
            compute() {
                return [
                    ...this.partners.map(partner => partner.persona),
                    ...this.guests.map(guest => guest.persona),
                ];
            },
        }),
    },
});
