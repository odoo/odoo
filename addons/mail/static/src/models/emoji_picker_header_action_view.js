/** @odoo-module **/

import { attr, clear, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiPickerHeaderActionView',
    template: 'mail.EmojiPickerHeaderActionView',
    templateGetter: 'emojiPickerHeaderActionView',
    identifyingMode: 'xor',
    fields: {
        // dummy identifying field, so that it works without defining one initially in mail
        __ownerAsDummy: one('EmojiPickerHeaderActionListView', { identifying: true, inverse: '__dummyActionView' }),
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
        owner: one('EmojiPickerHeaderActionListView', { inverse: 'actionViews', required: true,
            compute() {
                return clear();
            },
        }),
        sequence: attr({ default: 0 }),
    },
});
