/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallSidebarView',
    identifyingFields: ['callView'],
    fields: {
        callView: one('CallView', {
            inverse: 'callSidebarView',
            required: true,
            readonly: true,
        })
    },
});
