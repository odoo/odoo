/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'SnailmailNotificationPopoverContentView',
    recordMethods: {
        /**
         * @private
         * @returns {Message}
         */
        _computeMessage() {
            return this.popoverViewOwner.messageViewOwnerAsSnailmailNotificationContent.message;
        },
    },
    fields: {
        message: one('Message', {
            compute: '_computeMessage',
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'snailmailNotificationPopoverContentView',
        }),
    },
});
