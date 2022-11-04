/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'MessageNotificationPopoverContentView',
    template: 'mail.MessageNotificationPopoverContentView',
    templateGetter: 'messageNotificationPopoverContentView',
    fields: {
        messageView: one('MessageView', { related: 'popoverViewOwner.messageViewOwnerAsNotificationContent' }),
        popoverViewOwner: one('PopoverView', { identifying: true, inverse: 'messageNotificationPopoverContentView' }),
    },
});
