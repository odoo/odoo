/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussSidebarMailboxView',
    identifyingFields: [['discussViewOwnerAsHistory', 'discussViewOwnerAsInbox', 'discussViewOwnerAsStarred']],
    recordMethods: {
        /**
         * @private
         * @returns {Mailbox}
         */
        _computeMailbox() {
            if (this.discussViewOwnerAsHistory) {
                return replace(this.messaging.history);
            }
            if (this.discussViewOwnerAsInbox) {
                return replace(this.messaging.inbox);
            }
            if (this.discussViewOwnerAsStarred) {
                return replace(this.messaging.starred);
            }
            return clear();
        },
    },
    fields: {
        discussViewOwnerAsHistory: one('DiscussView', {
            inverse: 'historyView',
            readonly: true,
        }),
        discussViewOwnerAsInbox: one('DiscussView', {
            inverse: 'inboxView',
            readonly: true,
        }),
        discussViewOwnerAsStarred: one('DiscussView', {
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
