/** @odoo-module **/

import { clear, one, registerModel } from '@mail/model';

registerModel({
    name: 'MessageAuthorPrefixView',
    template: 'mail.MessageAuthorPrefixView',
    templateGetter: 'messageAuthorPrefixView',
    identifyingMode: 'xor',
    fields: {
        channelPreviewViewOwner: one('ChannelPreviewView', { identifying: true, inverse: 'messageAuthorPrefixView' }),
        message: one('Message', {
            compute() {
                if (this.channelPreviewViewOwner) {
                    return this.channelPreviewViewOwner.thread.lastMessage;
                }
                if (this.threadNeedactionPreviewViewOwner) {
                    return this.threadNeedactionPreviewViewOwner.thread.lastNeedactionMessageAsOriginThread;
                }
                return clear();
            },
        }),
        thread: one('Thread', {
            compute() {
                if (this.channelPreviewViewOwner) {
                    return this.channelPreviewViewOwner.thread;
                }
                if (this.threadNeedactionPreviewViewOwner) {
                    return this.threadNeedactionPreviewViewOwner.thread;
                }
                return clear();
            },
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', { identifying: true, inverse: 'messageAuthorPrefixView' }),
    },
});
