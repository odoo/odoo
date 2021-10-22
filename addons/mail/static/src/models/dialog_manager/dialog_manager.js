/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2many } from '@mail/model/model_field';

registerModel({
    name: 'mail.dialog_manager',
    identifyingFields: ['messaging'],
    fields: {
        // FIXME: dependent on implementation that uses insert order in relations!!
        dialogs: one2many('mail.dialog', {
            inverse: 'manager',
            isCausal: true,
        }),
    },
});
