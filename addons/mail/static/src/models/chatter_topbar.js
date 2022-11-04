/** @odoo-module **/

import { attr, clear, one, registerModel } from '@mail/model';

registerModel({
    name: 'ChatterTopbar',
    template: 'mail.ChatterTopbar',
    templateGetter: 'chatterTopbar',
    fields: {
        /**
         * Determines the label on the attachment button of the topbar.
         */
        attachmentButtonText: attr({ default: "",
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
        }),
        chatter: one('Chatter', { identifying: true, inverse: 'topbar' }),
    },
});
