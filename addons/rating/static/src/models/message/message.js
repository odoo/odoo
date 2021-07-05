/** @odoo-module **/

import { registerFieldPatchModel, registerInstancePatchModel, registerClassPatchModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerClassPatchModel('mail.message', 'rating/static/src/models/message.message.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('rating_value' in data) {
            data2.ratingValue = data.rating_value;
        }
        return data2;
    },
});

registerFieldPatchModel('mail.message', 'rating/static/src/models/message.message.js', {

    /**
     * The source url of the rating value image displayed,
     * converted from the rating value.
     */
    ratingImgSource: attr({
        compute: '_computeRatingImgSource',
        dependencies: [
            'ratingValue',
        ],
    }),

    /**
     * The original rating value.
     */
    ratingValue: attr(),
});

registerInstancePatchModel('mail.message', 'rating/static/src/models/message.message.js', {
    /**
     * @private
     */
    _computeRatingImgSource() {
        if (!this.ratingValue) {
            return null;
        }

        const RATING_LIMIT_SATISFIED = 5;
        const RATING_LIMIT_OK = 3;
        const RATING_LIMIT_MIN = 1
    
        let ratingInt = 0;
        if (this.ratingValue >= RATING_LIMIT_SATISFIED) {
            ratingInt = RATING_LIMIT_SATISFIED;
        } else if(this.ratingValue >= RATING_LIMIT_OK){
            ratingInt = RATING_LIMIT_OK;
        } else if (this.ratingValue >= RATING_LIMIT_MIN) {
            ratingInt = RATING_LIMIT_MIN;
        }
        return '/rating/static/src/img/rating_' + ratingInt + '.png';
    },

});
