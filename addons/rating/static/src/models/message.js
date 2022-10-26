/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
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
