/** @odoo-module **/

import { registerClassPatchModel } from '@mail/model/model_core';

registerClassPatchModel('mail.message', 'im_livechat/static/src/models/message/message.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('author_id' in data) {
            if (data.author_id[2]) {
                // flux specific for livechat, a 3rd param is livechat_username
                // and means 2nd param (display_name) should be ignored
                data2.author = [
                    ['insert-and-replace', {
                        id: data.author_id[0],
                        livechat_username: data.author_id[2],
                    }],
                ];
            }
        }
        return data2;
    },
});
