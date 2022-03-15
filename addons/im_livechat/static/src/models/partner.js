/** @odoo-module **/

import { addFields, addModelMethods, patchModelMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

// ensure that the model definition is loaded before the patch
import '@mail/models/partner';

let nextPublicId = -1;

addModelMethods('Partner', {
    getNextPublicId() {
        const id = nextPublicId;
        nextPublicId -= 1;
        return id;
    },
});

patchModelMethods('Partner', {
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
});

addFields('Partner', {
    /**
     * States the specific name of this partner in the context of livechat.
     * Either a string or undefined.
     */
    livechat_username: attr(),
});
