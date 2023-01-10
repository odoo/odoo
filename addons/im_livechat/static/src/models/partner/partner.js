/** @odoo-module **/

import { registerClassPatchModel, registerFieldPatchModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

let nextPublicId = -1;

registerClassPatchModel('mail.partner', 'im_livechat/static/src/models/partner/partner.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    convertData(data) {
        const data2 = this._super(data);
        if ('livechat_username' in data) {
            // flux specific, if livechat username is present it means `name`,
            // `email` and `im_status` contain `false` even though their value
            // might actually exist. Remove them from data2 to avoid overwriting
            // existing value (that could be known through other means).
            delete data2.name;
            delete data2.email;
            delete data2.im_status;
            data2.livechat_username = data.livechat_username;
        }
        return data2;
    },
    getNextPublicId() {
        const id = nextPublicId;
        nextPublicId -= 1;
        return id;
    },
});

registerFieldPatchModel('mail.partner', 'im_livechat/static/src/models/partner/partner.js', {
    /**
     * States the specific name of this partner in the context of livechat.
     * Either a string or undefined.
     */
    livechat_username: attr(),
});
