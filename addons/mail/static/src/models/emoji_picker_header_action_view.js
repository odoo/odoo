/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerHeaderActionView',
    identifyingMode: 'xor',
    fields: {
        // dummy identifying field, so that it works without defining one initially in mail
        __ownerAsDummy: one('EmojiPickerHeaderActionListView', {
            identifying: true,
            inverse: '__dummyActionView',
        }),
        content: one('Record', {
            compute() {
                return clear();
            },
            required: true,
        }),
        contentComponentName: attr({
            compute() {
                return clear();
            },
            required: true,
        }),
        owner: one('EmojiPickerHeaderActionListView', {
            compute() {
                return clear();
            },
            inverse: 'actionViews',
            required: true,
        }),
        sequence: attr({
            default: 0,
        }),
    },
});
