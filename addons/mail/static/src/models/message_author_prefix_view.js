/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageAuthorPrefixView',
    identifyingFields: [['threadNeedactionPreviewViewOwner', 'threadPreviewViewOwner']],
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
    },
    fields: {
        message: one('Message', {
            compute: '_computeMessage',
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            inverse: 'messageAuthorPrefixView',
            readonly: true,
        }),
        threadPreviewViewOwner: one('ThreadPreviewView', {
            inverse: 'messageAuthorPrefixView',
            readonly: true,
        }),
    },
});
