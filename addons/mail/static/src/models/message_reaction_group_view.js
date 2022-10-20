/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { markEventHandled } from '@mail/utils/utils';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'MessageReactionGroupView',
    template: 'mail.MessageReactionGroupView',
    templateGetter: 'messageReactionGroupView',
    recordMethods: {
        /**
         * Handles click on the reaction group.
         *
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            markEventHandled(ev, 'MessageReactionGroupView.Click');
            if (this.messageReactionGroup.hasUserReacted) {
                this.messageReactionGroup.message.removeReaction(this.messageReactionGroup.content);
            } else {
                this.messageReactionGroup.message.addReaction(this.messageReactionGroup.content);
            }
        },
    },
    fields: {
        messageReactionGroup: one('MessageReactionGroup', { identifying: true, inverse: 'messageReactionGroupViews' }),
        owner: one('MessageView', { identifying: true, inverse: 'messageReactionGroupViews' }),
        summary: attr({
            compute() {
                const {
                    length,
                    0: firstUser,
                    1: secondUser,
                    2: thirdUser,
                } = [
                    ...this.messageReactionGroup.partners.map(partner => {
                        if (this.messageReactionGroup.message.originThread) {
                            return this.messageReactionGroup.message.originThread.getMemberName(partner.persona);
                        }
                        return partner.nameOrDisplayName;
                    }),
                    ...this.messageReactionGroup.guests.map(guest => guest.name),
                ] || [];
                switch (length) {
                    case 1:
                        return sprintf(this.env._t('%s has reacted with %s'), firstUser, this.messageReactionGroup.content);
                    case 2:
                        return sprintf(this.env._t('%s and %s have reacted with %s'), firstUser, secondUser, this.messageReactionGroup.content);
                    case 3:
                        return sprintf(this.env._t('%s, %s, %s have reacted with %s'), firstUser, secondUser, thirdUser, this.messageReactionGroup.content);
                    case 4:
                        return sprintf(this.env._t('%s, %s, %s and 1 other person have reacted with %s'), firstUser, secondUser, thirdUser, this.messageReactionGroup.content);
                    default:
                        return sprintf(this.env._t('%s, %s, %s and %s other persons have reacted with %s'), firstUser, secondUser, thirdUser, length - 3, this.messageReactionGroup.content);
                }
            },
        }),
    },
});
