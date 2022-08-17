/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussSidebarMailboxView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @private
         * @returns {Mailbox}
         */
        _computeMailbox() {
            if (this.discussViewOwnerAsHistory) {
                return this.messaging.history;
            }
            if (this.discussViewOwnerAsInbox) {
                return this.messaging.inbox;
            }
            if (this.discussViewOwnerAsStarred) {
                return this.messaging.starred;
            }
            return clear();
        },
    },
    fields: {
        discussViewOwnerAsHistory: one('DiscussView', {
            identifying: true,
            inverse: 'historyView',
            readonly: true,
        }),
        discussViewOwnerAsInbox: one('DiscussView', {
            identifying: true,
            inverse: 'inboxView',
            readonly: true,
        }),
        discussViewOwnerAsStarred: one('DiscussView', {
            identifying: true,
            inverse: 'starredView',
            readonly: true,
        }),
        mailbox: one('Mailbox', {
            compute: '_computeMailbox',
            readonly: true,
            required: true,
        }),
    },
});
