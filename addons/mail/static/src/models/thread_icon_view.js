/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadIconView',
    template: 'mail.ThreadIconView',
    templateGetter: 'threadIconView',
    identifyingMode: 'xor',
    fields: {
        chatWindowHeaderViewOwner: one('ChatWindowHeaderView', { identifying: true, inverse: 'threadIconView' }),
        discussSidebarCategoryItemOwner: one('DiscussSidebarCategoryItem', { identifying: true, inverse: 'threadIconView' }),
        discussSidebarMailboxViewOwner: one('DiscussSidebarMailboxView', { identifying: true, inverse: 'threadIconView' }),
        thread: one('Thread', { required: true,
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
                    return this.threadViewTopbarOwner.thread;
                }
            },
        }),
        threadTypingIconView: one('ThreadTypingIconView', { inverse: 'threadIconViewOwner',
            compute() {
                if (
                    this.thread.channel &&
                    this.thread.channel.channel_type === 'chat' &&
                    this.thread.channel.correspondent &&
                    this.thread.orderedOtherTypingMembers.length > 0
                ) {
                    return {};
                }
                return clear();
            },
        }),
        threadViewTopbarOwner: one('ThreadViewTopbar', { identifying: true, inverse: 'threadIconView' }),
    },
});
