/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/message_view';

addFields('MessageView', {
    snailmailErrorDialog: one('Dialog', {
        inverse: 'messageViewOwnerAsSnailmailError',
        isCausal: true,
    }),
    snailmailNotificationPopoverView: one('PopoverView', {
        inverse: 'messageViewOwnerAsSnailmailNotificationContent',
        isCausal: true,
    }),
});

patchRecordMethods('MessageView', {
    /**
     * @override
     */
    onClickFailure() {
        if (this.message.message_type === 'snailmail') {
            /**
             * Messages from snailmail are considered to have at most one
             * notification. The failure type of the whole message is considered
             * to be the same as the one from that first notification, and the
             * click action will depend on it.
             */
            switch (this.message.notifications[0].failure_type) {
                case 'sn_credit':
                    // URL only used in this component, not received at init
                    this.messaging.fetchSnailmailCreditsUrl();
                    this.update({ snailmailErrorDialog: {} });
                    break;
                case 'sn_error':
                    this.update({ snailmailErrorDialog: {} });
                    break;
                case 'sn_fields':
                    this.message.openMissingFieldsLetterAction();
                    break;
                case 'sn_format':
                    this.message.openFormatLetterAction();
                    break;
                case 'sn_price':
                    this.update({ snailmailErrorDialog: {} });
                    break;
                case 'sn_trial':
                    // URL only used in this component, not received at init
                    this.messaging.fetchSnailmailCreditsUrlTrial();
                    this.update({ snailmailErrorDialog: {} });
                    break;
            }
        } else {
            this._super(...arguments);
        }
    },
    onClickNotificationIcon() {
        if (this.message && this.message.message_type === 'snailmail') {
            this.update({ snailmailNotificationPopoverView: this.snailmailNotificationPopoverView ? clear() : {} });
            return;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeFailureNotificationIconClassName() {
        if (this.message && this.message.message_type === 'snailmail') {
            return 'fa fa-paper-plane';
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeNotificationIconClassName() {
        if (this.message && this.message.message_type === 'snailmail') {
            return 'fa fa-paper-plane';
        }
        return this._super();
    },
});
