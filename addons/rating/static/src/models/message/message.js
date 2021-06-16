/** @odoo-module **/
import { registerFieldPatchModel, registerClassPatchModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerFieldPatchModel('mail.message', 'rating/static/src/models/message.message.js', {
    /**
     * The source url of the rating value image displayed,
     * converted from the rating values.
     */
    ratingImgSource: attr(),
});

function _get_rating_image_filename(rating_val) {
    const RATING_LIMIT_SATISFIED = 5;
    const RATING_LIMIT_OK = 3;
    const RATING_LIMIT_MIN = 1

    let rating_int = 0;
    if (rating_val >= RATING_LIMIT_SATISFIED) {
        rating_int = RATING_LIMIT_SATISFIED;
    } else if( rating_val >= RATING_LIMIT_OK ){
        rating_int = RATING_LIMIT_OK;
    } else if ( rating_val >= RATING_LIMIT_MIN ) {
        rating_int = RATING_LIMIT_MIN;
    }
    return 'rating_' + rating_int + '.png';
}

registerClassPatchModel('mail.message', 'rating/static/src/models/message.message.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('rating_val' in data) {
            data2.ratingImgSource = '/rating/static/src/img/' + _get_rating_image_filename(data.rating_val);
        }
        return data2;
    },
});
