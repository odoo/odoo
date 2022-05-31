/** @odoo-module **/

import { addFields, patchModelMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure the model definition is loaded before the patch
import '@mail/models/message';

patchModelMethods('Message', {
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

});

addFields('Message', {
    rating: one('Rating', {
        isCausal: true,
    }),
});
