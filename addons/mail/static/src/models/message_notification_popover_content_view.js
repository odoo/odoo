/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MessageNotificationPopoverContentView',
    identifyingFields: ['popoverViewOwner'],
    fields: {
        popoverViewOwner: one('PopoverView', {
            inverse: 'messageNotificationPopoverContentView',
            readonly: true,
            required: true,
        }),
    },
});
