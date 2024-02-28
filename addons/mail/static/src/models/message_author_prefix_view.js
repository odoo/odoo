/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageAuthorPrefixView',
    identifyingMode: 'xor',
    fields: {
        channelPreviewViewOwner: one('ChannelPreviewView', {
            identifying: true,
            inverse: 'messageAuthorPrefixView',
        }),
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
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            identifying: true,
            inverse: 'messageAuthorPrefixView',
        }),
    },
});
