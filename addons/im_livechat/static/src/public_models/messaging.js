/** @odoo-module **/

import { one, registerPatch } from '@mail/model';

registerPatch({
    name: 'Messaging',
    fields: {
        publicLivechatGlobal: one('PublicLivechatGlobal', {
            isCausal: true,
        }),
    },
});
