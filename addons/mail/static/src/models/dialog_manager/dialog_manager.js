/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2many } from '@mail/model/model_field';

registerModel({
    name: 'DialogManager',
    identifyingFields: ['messaging'],
    fields: {
        // FIXME: dependent on implementation that uses insert order in relations!!
        dialogs: one2many('Dialog', {
            inverse: 'manager',
            isCausal: true,
        }),
    },
});
