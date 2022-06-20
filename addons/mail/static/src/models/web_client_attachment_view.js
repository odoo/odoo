/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'WebClientAttachmentView',
    identifyingFields: ['webClientViewOwner'],
    fields: {
        thread: one('Thread', {
            related: 'webClientViewOwner.thread'
        }),
        webClientViewOwner: one('WebClientView', {
            inverse: 'webClientAttachmentView',
            readonly: true,
            required: true,
        }),
    },
});
