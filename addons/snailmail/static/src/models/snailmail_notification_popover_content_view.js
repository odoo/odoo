/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'SnailmailNotificationPopoverContentView',
    identifyingFields: ['popoverViewOwner'],
    fields: {
        popoverViewOwner: one('PopoverView', {
            inverse: 'snailmailNotificationPopoverContentView',
            readonly: true,
            required: true,
        }),
    },
});
