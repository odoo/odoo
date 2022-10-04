/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Mailbox',
    identifyingMode: 'xor',
    recordMethods: {
        _onChangeCounter() {
            if (this !== this.global.Messaging.inbox) {
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
            compute() {
                switch (this) {
                    case this.global.Messaging.history:
                        return '/mail/history/messages';
                    case this.global.Messaging.inbox:
                        return '/mail/inbox/messages';
                    case this.global.Messaging.starred:
                        return '/mail/starred/messages';
                    default:
                        return clear();
                }
            },
        }),
        /**
         * Useful to fill its inverse `Messaging/allMailboxes`.
         */
        messagingAsAnyMailbox: one('Messaging', {
            compute() {
                if (!this.global.Messaging) {
                    return clear();
                }
                return this.global.Messaging;
            },
            inverse: 'allMailboxes',
        }),
        messagingAsHistory: one('Messaging', {
            identifying: true,
            inverse: 'history',
        }),
        messagingAsInbox: one('Messaging', {
            identifying: true,
            inverse: 'inbox',
        }),
        messagingAsStarred: one('Messaging', {
            identifying: true,
            inverse: 'starred',
        }),
        name: attr({
            compute() {
                switch (this) {
                    case this.global.Messaging.history:
                        return this.env._t("History");
                    case this.global.Messaging.inbox:
                        return this.env._t("Inbox");
                    case this.global.Messaging.starred:
                        return this.env._t("Starred");
                    default:
                        return clear();
                }
            },
        }),
        /**
         * Useful to display rainbow man on inbox.
         */
        previousValueOfInboxCounter: attr({
            default: 0,
        }),
        sequence: attr({
            compute() {
                switch (this) {
                    case this.global.Messaging.history:
                        return 2;
                    case this.global.Messaging.inbox:
                        return 0;
                    case this.global.Messaging.starred:
                        return 1;
                    default:
                        return clear();
                }
            },
        }),
        thread: one('Thread', {
            compute() {
                const threadId = (() => {
                    switch (this) {
                        case this.global.Messaging.history:
                            return 'history';
                        case this.global.Messaging.inbox:
                            return 'inbox';
                        case this.global.Messaging.starred:
                            return 'starred';
                    }
                })();
                if (!threadId) {
                    return clear();
                }
                return {
                    id: threadId,
                    model: 'mail.box',
                };
            },
            inverse: 'mailbox',
        }),
    },
    onChanges: [
        {
            dependencies: ['counter'],
            methodName: '_onChangeCounter',
        },
    ],
});
