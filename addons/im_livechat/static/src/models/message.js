/** @odoo-module **/

import { patchModelMethods } from '@mail/model/model_core';
import { insertAndReplace } from '@mail/model/model_field_command';
// ensure the model definition is loaded before the patch
import '@mail/models/message';

patchModelMethods('Message', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('author_id' in data) {
            if (data.author_id[2]) {
                // flux specific for livechat, a 3rd param is livechat_username
                // and means 2nd param (display_name) should be ignored
                data2.author = insertAndReplace({
                    id: data.author_id[0],
                    livechat_username: data.author_id[2],
                });
            }
        }
        return data2;
    },
});
