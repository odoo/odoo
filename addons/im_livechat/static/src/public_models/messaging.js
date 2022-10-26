/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'Messaging',
    fields: {
        publicLivechatGlobal: one('PublicLivechatGlobal', {
            isCausal: true,
        }),
    },
});
