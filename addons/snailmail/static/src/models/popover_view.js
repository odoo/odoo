/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/popover_view';

addFields('PopoverView', {
    snailmailNotificationPopoverContentView: one('SnailmailNotificationPopoverContentView', {
        compute: '_computeSnailmailNotificationPopoverContentView',
        inverse: 'popoverViewOwner',
        isCausal: true,
        readonly: true,
    }),
});

addRecordMethods('PopoverView', {
    /**
     * @override
     */
    _computeSnailmailNotificationPopoverContentView() {
        if (this.messageViewOwnerAsMessageNotification && this.messageViewOwnerAsMessageNotification.message.message_type === 'snailmail') {
            return insertAndReplace();
        }
        return clear();
    },
});

patchRecordMethods('PopoverView', {
    /**
     * @override
     */
    _computeContent() {
        if (this.snailmailNotificationPopoverContentView) {
            return replace(this.snailmailNotificationPopoverContentView);   
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeContentComponentName() {
        if (this.snailmailNotificationPopoverContentView) {
            return 'SnailmailNotificationPopoverContent';
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeMessageNotificationPopoverContentView() {
        if (this.messageViewOwnerAsMessageNotification && this.messageViewOwnerAsMessageNotification.message.message_type === 'snailmail') {
            /**
             * It was decided that the information displayed for snailmail messages
             * has to be different than for standard messages, see task-1907998.
             */
            return clear();
        }
        return this._super();
    },
    /**
     * @override
     */
    _computePosition() {
        if (this.snailmailNotificationPopoverContentView) {
            return 'top-start';
        }
        return this._super();
    },
});
