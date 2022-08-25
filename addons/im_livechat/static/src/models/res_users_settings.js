/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import '@mail/models/res_users_settings'; // ensure the model definition is loaded before the patch

addFields('res.users.settings', {
    is_discuss_sidebar_category_livechat_open: attr({
        default: true,
    }),
});
