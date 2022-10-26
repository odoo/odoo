/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadTextualTypingStatusView',
    fields: {
        owner: one('ComposerView', {
            identifying: true,
            inverse: 'threadTextualTypingStatusView',
        }),
        thread: one('Thread', {
            compute() {
                return this.owner.composer.activeThread;
            },
            required: true,
        }),
        threadTypingIconView: one('ThreadTypingIconView', {
            compute() {
                if (this.thread.orderedOtherTypingMembers.length > 0) {
                    return {};
                }
                return clear();
            },
            inverse: 'threadTextualTypingStatusViewOwner',
        }),
    },
});
