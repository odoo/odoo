/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadTypingIconView',
    template: 'mail.ThreadTypingIconView',
    identifyingMode: 'xor',
    fields: {
        size: attr({ default: 'small',
            compute() {
                if (this.threadTextualTypingStatusViewOwner) {
                    return 'medium';
                }
                return clear();
            },
        }),
        threadIconViewOwner: one('ThreadIconView', { identifying: true, inverse: 'threadTypingIconView' }),
        threadTextualTypingStatusViewOwner: one('ThreadTextualTypingStatusView', { identifying: true, inverse: 'threadTypingIconView' }),
        title: attr({
            compute() {
                if (this.threadIconViewOwner) {
                    return this.threadIconViewOwner.thread.typingStatusText;
                }
                return clear();
            },
        }),
    },
});
