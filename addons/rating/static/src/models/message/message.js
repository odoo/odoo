/** @odoo-module **/
import { registerFieldPatchModel, registerClassPatchModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerFieldPatchModel('mail.message', 'rating/static/src/models/message.message.js', {
    ratingImg: attr(),
});
    
registerClassPatchModel('mail.message', 'rating/static/src/models/message.message.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('rating_img' in data) {
            data2.ratingImg = data.rating_img;
        }
        return data2;
    },
});
