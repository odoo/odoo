/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
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
        compute: '_computeSnailmailNotificationPopoverContentView',
        inverse: 'popoverViewOwner',
        isCausal: true,
    }),
});

addRecordMethods('PopoverView', {
    /**
     * @private
     * @returns {Object|FieldCommand}
     */
    _computeSnailmailNotificationPopoverContentView() {
        if (this.messageViewOwnerAsSnailmailNotificationContent) {
            return {};
        }
        return clear();
    },
});

patchRecordMethods('PopoverView', {
    /**
     * @override
     */
    _computeAnchorRef() {
        if (this.messageViewOwnerAsSnailmailNotificationContent) {
            return this.messageViewOwnerAsSnailmailNotificationContent.notificationIconRef;
        }
        return this._super();
    },
    /**
     * @override
     */
     _computeContent() {
        if (this.snailmailNotificationPopoverContentView) {
            return this.snailmailNotificationPopoverContentView;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeContentComponentName() {
        if (this.snailmailNotificationPopoverContentView) {
            return 'SnailmailNotificationPopoverContentView';
        }
        return this._super();
    },
});
