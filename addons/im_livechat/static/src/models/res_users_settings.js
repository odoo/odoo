/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerPatch({
    name: 'res.users.settings',
    fields: {
        is_discuss_sidebar_category_livechat_open: attr({
            default: true,
        }),
    },
});
