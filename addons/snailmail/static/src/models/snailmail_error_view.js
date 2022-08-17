/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'SnailmailErrorView',
    recordMethods: {
        /**
         * Returns whether the given html element is inside this snailmail error view.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        onClickCancelLetter() {
            this.message.cancelLetter();
            this.dialogOwner.delete();
        },
        onClickClose() {
            this.dialogOwner.delete();
        },
        onClickResendLetter() {
            this.message.resendLetter();
            this.dialogOwner.delete();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasCreditsError() {
            return Boolean(
                this.notification &&
                (
                    this.notification.failure_type === 'sn_credit' ||
                    this.notification.failure_type === 'sn_trial'
                )
            );
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessage() {
            return this.dialogOwner.messageViewOwnerAsSnailmailError.message;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotification() {
            return this.message.notifications[0];
        },
    },
    fields: {
        component: attr(),
        dialogOwner: one('Dialog', {
            identifying: true,
            inverse: 'snailmailErrorView',
        }),
        hasCreditsError: attr({
            compute: '_computeHasCreditsError',
        }),
        message: one('Message', {
            compute: '_computeMessage',
            required: true,
        }),
        /**
         * Messages from snailmail are considered to have at most one notification.
         */
        notification: one('Notification', {
            compute: '_computeNotification',
            required: true,
        }),
    },
});
