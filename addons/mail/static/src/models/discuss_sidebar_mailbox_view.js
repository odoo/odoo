/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussSidebarMailboxView',
    identifyingMode: 'xor',
    fields: {
        discussViewOwnerAsHistory: one('DiscussView', {
            identifying: true,
            inverse: 'historyView',
        }),
        discussViewOwnerAsInbox: one('DiscussView', {
            identifying: true,
            inverse: 'inboxView',
        }),
        discussViewOwnerAsStarred: one('DiscussView', {
            identifying: true,
            inverse: 'starredView',
        }),
        mailbox: one('Mailbox', {
            compute() {
                if (this.discussViewOwnerAsHistory) {
                    return this.global.Messaging.history;
                }
                if (this.discussViewOwnerAsInbox) {
                    return this.global.Messaging.inbox;
                }
                if (this.discussViewOwnerAsStarred) {
                    return this.global.Messaging.starred;
                }
                return clear();
            },
            required: true,
        }),
    },
});
