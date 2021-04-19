/** @odoo-module **/
import { registerFieldPatchModel, registerClassPatchModel } from 'mail/static/src/model/model_core.js';

const { attr } = require('mail/static/src/model/model_field.js');

registerFieldPatchModel('mail.message', 'project/static/src/models/message.message.js', {
    ratingVal: attr(),
});
    
registerClassPatchModel('mail.message', 'project/static/src/models/message.message.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('rating_val' in data) {
            data2.ratingVal = data.rating_val;
        }
        return data2;
    },
});
