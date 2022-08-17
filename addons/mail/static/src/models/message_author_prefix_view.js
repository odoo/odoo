/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageAuthorPrefixView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessage() {
            if (this.threadNeedactionPreviewViewOwner) {
                return replace(this.threadNeedactionPreviewViewOwner.thread.lastNeedactionMessageAsOriginThread);
            }
            if (this.threadPreviewViewOwner) {
                return replace(this.threadPreviewViewOwner.thread.lastMessage);
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
            if (this.threadPreviewViewOwner) {
                return replace(this.threadPreviewViewOwner.thread);
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
            identifying: true,
            inverse: 'messageAuthorPrefixView',
            readonly: true,
        }),
        threadPreviewViewOwner: one('ThreadPreviewView', {
            identifying: true,
            inverse: 'messageAuthorPrefixView',
            readonly: true,
        }),
    },
});
