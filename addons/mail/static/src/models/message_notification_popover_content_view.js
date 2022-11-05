/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'MessageNotificationPopoverContentView',
    template: 'mail.MessageNotificationPopoverContentView',
    fields: {
        messageView: one('MessageView', { related: 'popoverViewOwner.messageViewOwnerAsNotificationContent' }),
        popoverViewOwner: one('PopoverView', { identifying: true, inverse: 'messageNotificationPopoverContentView' }),
    },
});
