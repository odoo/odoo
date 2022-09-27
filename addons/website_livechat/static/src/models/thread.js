/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';

registerPatch({
    name: 'Thread',
    modelMethods: {
        /**
         * @override
         */
        convertData(data) {
            const data2 = this._super(data);
            if ('visitor' in data) {
                if (data.visitor) {
                    data2.visitor = insert(this.messaging.models['Visitor'].convertData(data.visitor));
                } else {
                    data2.visitor = clear();
                }
            }
            return data2;
        },
    },
    fields: {
        /**
         * Visitor connected to the livechat.
         */
        visitor: one('Visitor', {
            inverse: 'threads',
        }),
    },
});
