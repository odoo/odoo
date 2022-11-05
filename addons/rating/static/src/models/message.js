/** @odoo-module **/

import { one, Patch } from '@mail/model';

Patch({
    name: 'Message',
    modelMethods: {
        /**
         * @override
         */
        convertData(data) {
            const data2 = this._super(data);
            if ('rating' in data) {
                data2.rating = data.rating;
            }
            return data2;
        },
    },
    fields: {
        rating: one('Rating', {
            isCausal: true,
        }),
    },
});
