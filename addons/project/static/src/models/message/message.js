/** @odoo-module **/
import { registerFieldPatchModel, registerClassPatchModel } from 'mail/static/src/model/model_core.js';

registerFieldPatchModel('mail.message', 'project/static/src/models/message.message.js', {
    isRating: attr(),
});
    
registerClassPatchModel('mail.message', 'project/static/src/models/message.message.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('is_rating' in data) {
            data2.isRating = data.is_rating;
        }
        return data2;
    },
});