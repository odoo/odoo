/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'Mailbox',
    identifyingFields: [['messagingAsHistory', 'messagingAsInbox', 'messagingAsStarred']],
    recordMethods: {
        /**
         * @returns {string|FieldCommand}
         */
        _computeFetchMessagesUrl() {
            switch (this) {
                case this.messaging.history:
                    return '/mail/history/messages';
                case this.messaging.inbox:
                    return '/mail/inbox/messages';
                case this.messaging.starred:
                    return '/mail/starred/messages';
                default:
                    return clear();
            }
        },
        /**
         * @returns {FieldCommand}
         */
        _computeMessagingAsAnyMailbox() {
            if (!this.messaging) {
                return clear();
            }
            return replace(this.messaging);
        },
        /**
         * @returns {string|FieldCommand}
         */
        _computeName() {
            switch (this) {
                case this.messaging.history:
                    return this.env._t("History");
                case this.messaging.inbox:
                    return this.env._t("Inbox");
                case this.messaging.starred:
                    return this.env._t("Starred");
                default:
                    return clear();
            }
        },
        /**
         * @returns {integer|FieldCommand}
         */
        _computeSequence() {
            switch (this) {
                case this.messaging.history:
                    return 2;
                case this.messaging.inbox:
                    return 0;
                case this.messaging.starred:
                    return 1;
                default:
                    return clear();
            }
        },
        /**
         * @returns {FieldCommand}
         */
        _computeThread() {
            const threadId = (() => {
                switch (this) {
                    case this.messaging.history:
                        return 'history';
                    case this.messaging.inbox:
                        return 'inbox';
                    case this.messaging.starred:
                        return 'starred';
                }
            })();
            if (!threadId) {
                return clear();
            }
            return insertAndReplace({
                id: threadId,
                model: 'mail.box',
            });
        },
        _onChangeCounter() {
            if (this !== this.messaging.inbox) {
                return;
            }
            if (
                this.thread.threadViews.length > 0 &&
                this.previousValueOfInboxCounter > 0 && this.counter === 0
            ) {
                this.env.services.effect.add({
                    message: this.env._t("Congratulations, your inbox is empty!"),
                    type: 'rainbow_man',
                });
            }
            this.update({ previousValueOfInboxCounter: this.counter });
        },
    },
    fields: {
        counter: attr({
            default: 0,
        }),
        fetchMessagesUrl: attr({
            compute: '_computeFetchMessagesUrl',
        }),
        /**
         * Useful to fill its inverse `Messaging/allMailboxes`.
         */
        messagingAsAnyMailbox: one('Messaging', {
            compute: '_computeMessagingAsAnyMailbox',
            inverse: 'allMailboxes',
        }),
        messagingAsHistory: one('Messaging', {
            inverse: 'history',
            readonly: true,
        }),
        messagingAsInbox: one('Messaging', {
            inverse: 'inbox',
            readonly: true,
        }),
        messagingAsStarred: one('Messaging', {
            inverse: 'starred',
            readonly: true,
        }),
        name: attr({
            compute: '_computeName',
        }),
        /**
         * Useful to display rainbow man on inbox.
         */
        previousValueOfInboxCounter: attr({
            default: 0,
        }),
        sequence: attr({
            compute: '_computeSequence',
        }),
        thread: one('Thread', {
            compute: '_computeThread',
            inverse: 'mailbox',
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['counter'],
            methodName: '_onChangeCounter',
        }),
    ],
});
