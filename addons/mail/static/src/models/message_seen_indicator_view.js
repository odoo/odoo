/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageSeenIndicatorView',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageSeenIndicator() {
            if (this.messageViewOwner.messageListViewItemOwner && this.messageViewOwner.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread) {
                return {
                    message: this.messageViewOwner.message,
                    thread: this.messageViewOwner.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread,
                };
            }
            return clear();
        },
    },
    fields: {
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'messageSeenIndicatorView',
        }),
        messageSeenIndicator: one('MessageSeenIndicator', {
            compute: '_computeMessageSeenIndicator',
        }),
    },
});
