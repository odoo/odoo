/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ThreadIconView',
    identifyingMode: 'xor',
    fields: {
        chatWindowHeaderViewOwner: one('ChatWindowHeaderView', {
            identifying: true,
            inverse: 'threadIconView',
        }),
        discussSidebarCategoryItemOwner: one('DiscussSidebarCategoryItem', {
            identifying: true,
            inverse: 'threadIconView',
        }),
        discussSidebarMailboxViewOwner: one('DiscussSidebarMailboxView', {
            identifying: true,
            inverse: 'threadIconView',
        }),
        thread: one('Thread', {
            compute() {
                if (this.chatWindowHeaderViewOwner) {
                    return this.chatWindowHeaderViewOwner.chatWindowOwner.thread;
                }
                if (this.discussSidebarCategoryItemOwner) {
                    return this.discussSidebarCategoryItemOwner.thread;
                }
                if (this.discussSidebarMailboxViewOwner) {
                    return this.discussSidebarMailboxViewOwner.mailbox.thread;
                }
                if (this.threadViewTopbarOwner) {
                    return this.threadViewTopbarOwner.thread
                }
            },
            required: true,
        }),
        threadViewTopbarOwner: one('ThreadViewTopbar', {
            identifying: true,
            inverse: 'threadIconView',
        }),
    },
});
