/** @odoo-module **/

import { addModelNamesToFetch, insertModelFields } from '@mail/../tests/helpers/model_definitions_helpers';

addModelNamesToFetch(['im_livechat.channel']);
insertModelFields('res.users.settings', {
    is_discuss_sidebar_category_livechat_open: { default: true },
});
