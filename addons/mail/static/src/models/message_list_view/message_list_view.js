/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'MessageListView',
    identifyingFields: ['threadViewOwner'],
    fields: {
        /**
         * States the OWL component of this message list view
         */
        component: attr(),
        threadViewOwner: one('ThreadView', {
            inverse: 'messageListView',
            readonly: true,
            required: true,
        }),
    },
});
