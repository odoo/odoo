/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageAuthorPrefixView',
    identifyingFields: [['threadNeedactionPreviewViewOwner', 'channelPreviewViewOwner']],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessage() {
            if (this.threadNeedactionPreviewViewOwner) {
                return replace(this.threadNeedactionPreviewViewOwner.thread.lastNeedactionMessageAsOriginThread);
            }
            if (this.channelPreviewViewOwner) {
                return replace(this.channelPreviewViewOwner.channel.thread.lastMessage);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            if (this.threadNeedactionPreviewViewOwner) {
                return replace(this.threadNeedactionPreviewViewOwner.thread);
            }
            if (this.channelPreviewViewOwner) {
                return replace(this.channelPreviewViewOwner.channel.thread);
            }
            return clear();
        },
    },
    fields: {
        message: one('Message', {
            compute: '_computeMessage',
        }),
        thread: one('Thread', {
            compute: '_computeThread',
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            inverse: 'messageAuthorPrefixView',
            readonly: true,
        }),
        channelPreviewViewOwner: one('ChannelPreviewView', {
            inverse: 'messageAuthorPrefixView',
            readonly: true,
        }),
    },
});
