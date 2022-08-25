/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many } from '@mail/model/model_field';

registerModel({
    name: 'DialogManager',
    fields: {
        // FIXME: dependent on implementation that uses insert order in relations!!
        dialogs: many('Dialog', {
            inverse: 'manager',
            isCausal: true,
        }),
    },
});
