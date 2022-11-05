/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { attr, one, Model } from '@mail/model';

Model({
    name: 'SnailmailErrorView',
    template: 'snailmail.SnailmailErrorView',
    componentSetup() {
        useComponentToModel({ fieldName: 'component' });
    },
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
    },
    fields: {
        component: attr(),
        dialogOwner: one('Dialog', {
            identifying: true,
            inverse: 'snailmailErrorView',
        }),
        hasCreditsError: attr({
            compute() {
                return Boolean(
                    this.notification &&
                    (
                        this.notification.failure_type === 'sn_credit' ||
                        this.notification.failure_type === 'sn_trial'
                    )
                );
            },
        }),
        message: one('Message', {
            compute() {
                return this.dialogOwner.messageViewOwnerAsSnailmailError.message;
            },
            required: true,
        }),
        /**
         * Messages from snailmail are considered to have at most one notification.
         */
        notification: one('Notification', {
            compute() {
                return this.message.notifications[0];
            },
            required: true,
        }),
    },
});
