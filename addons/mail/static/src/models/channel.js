/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'Channel',
    identifyingFields: ['id'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            return insertAndReplace({
                id: this.id,
                model: 'mail.channel',
            });
        },
    },
    fields: {
        id: attr({
            readonly: true,
            required: true,
        }),
        thread: one('Thread', {
            compute: '_computeThread',
            inverse: 'channelOwner',
            isCausal: true,
            readonly: true,
            required: true,
        })
    },
});
