/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerHeaderActionView',
    template: 'mail.EmojiPickerHeaderActionView',
    identifyingMode: 'xor',
    fields: {
        // dummy identifying field, so that it works without defining one initially in mail
        __ownerAsDummy: one('EmojiPickerView', { identifying: true, inverse: '__dummyActionView', }),
        content: one('Record', { required: true,
            compute() {
                return clear();
            },
        }),
        contentComponentName: attr({ required: true,
            compute() {
                return clear();
            },
        }),
        owner: one('EmojiPickerView', { inverse: 'actionViews', required: true,
            compute() {
                return clear();
            },
        }),
        sequence: attr({ default: 0 }),
    },
});
