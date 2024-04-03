/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ChatterTopbar',
    fields: {
        /**
         * Determines the label on the attachment button of the topbar.
         */
        attachmentButtonText: attr({
            compute() {
                if (!this.chatter || !this.chatter.thread) {
                    return clear();
                }
                const attachments = this.chatter.thread.allAttachments;
                if (attachments.length === 0) {
                    return clear();
                }
                return attachments.length;
            },
            default: "",
        }),
        chatter: one('Chatter', {
            identifying: true,
            inverse: 'topbar',
        }),
    },
});
