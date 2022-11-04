/** @odoo-module **/

import { attr, registerPatch } from '@mail/model';

registerPatch({
    name: 'res.users.settings',
    fields: {
        is_discuss_sidebar_category_livechat_open: attr({
            default: true,
        }),
    },
});
