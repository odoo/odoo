/** @odoo-module **/

import { addFields, patchFields } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/popover_view';

addFields('PopoverView', {
    messageViewOwnerAsSnailmailNotificationContent: one('MessageView', {
        identifying: true,
        inverse: 'snailmailNotificationPopoverView',
    }),
    snailmailNotificationPopoverContentView: one('SnailmailNotificationPopoverContentView', {
        compute() {
            if (this.messageViewOwnerAsSnailmailNotificationContent) {
                return {};
            }
            return clear();
        },
        inverse: 'popoverViewOwner',
    }),
});

patchFields('PopoverView', {
    anchorRef: {
        compute() {
            if (this.messageViewOwnerAsSnailmailNotificationContent) {
                return this.messageViewOwnerAsSnailmailNotificationContent.notificationIconRef;
            }
            return this._super();
        },
    },
    content: {
        compute() {
            if (this.snailmailNotificationPopoverContentView) {
                return this.snailmailNotificationPopoverContentView;
            }
            return this._super();
        },
    },
    contentComponentName: {
        compute() {
            if (this.snailmailNotificationPopoverContentView) {
                return 'SnailmailNotificationPopoverContentView';
            }
            return this._super();
        },
    },
});
