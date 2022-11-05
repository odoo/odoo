/** @odoo-module **/

import { clear, insert, one, Patch } from '@mail/model';

Patch({
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
