/** @odoo-module **/

import { clear, one, registerModel } from '@mail/model';

registerModel({
    name: 'MessageSeenIndicatorView',
    template: 'mail.MessageSeenIndicatorView',
    templateGetter: 'messageSeenIndicatorView',
    fields: {
        messageViewOwner: one('MessageView', { identifying: true, inverse: 'messageSeenIndicatorView' }),
        messageSeenIndicator: one('MessageSeenIndicator', {
            compute() {
                if (this.messageViewOwner.messageListViewItemOwner && this.messageViewOwner.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread) {
                    return {
                        message: this.messageViewOwner.message,
                        thread: this.messageViewOwner.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread,
                    };
                }
                return clear();
            },
        }),
    },
});
