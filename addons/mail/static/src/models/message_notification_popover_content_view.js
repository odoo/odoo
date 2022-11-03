/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MessageNotificationPopoverContentView',
    template: 'mail.MessageNotificationPopoverContentView',
    templateGetter: 'messageNotificationPopoverContentView',
    fields: {
        messageView: one('MessageView', { related: 'popoverViewOwner.messageViewOwnerAsNotificationContent' }),
        popoverViewOwner: one('PopoverView', { identifying: true, inverse: 'messageNotificationPopoverContentView' }),
    },
});
