/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageAuthorPrefixView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessage() {
            if (this.channelPreviewViewOwner) {
                return this.channelPreviewViewOwner.thread.lastMessage;
            }
            if (this.threadNeedactionPreviewViewOwner) {
                return this.threadNeedactionPreviewViewOwner.thread.lastNeedactionMessageAsOriginThread;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            if (this.channelPreviewViewOwner) {
                return this.channelPreviewViewOwner.thread;
            }
            if (this.threadNeedactionPreviewViewOwner) {
                return this.threadNeedactionPreviewViewOwner.thread;
            }
            return clear();
        },
    },
    fields: {
        channelPreviewViewOwner: one('ChannelPreviewView', {
            identifying: true,
            inverse: 'messageAuthorPrefixView',
        }),
        message: one('Message', {
            compute: '_computeMessage',
        }),
        thread: one('Thread', {
            compute: '_computeThread',
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            identifying: true,
            inverse: 'messageAuthorPrefixView',
        }),
    },
});
