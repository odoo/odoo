/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MessageSeenIndicatorView',
    identifyingFields: ['messageViewOwner'],
    fields: {
        messageViewOwner: one('MessageView', {
            inverse: 'messageSeenIndicatorView',
            readonly: true,
            required: true,
        }),
    },
});
