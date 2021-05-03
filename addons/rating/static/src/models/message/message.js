/** @odoo-module **/
import { registerFieldPatchModel, registerClassPatchModel } from 'mail/static/src/model/model_core.js';

const { attr } = require('mail/static/src/model/model_field.js');

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
