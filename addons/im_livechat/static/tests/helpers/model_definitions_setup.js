/** @odoo-module **/

import { addModelNamesToFetch, insertModelFields } from '@bus/../tests/helpers/model_definitions_helpers';

addModelNamesToFetch(['im_livechat.channel']);
insertModelFields('res.users.settings', {
    is_discuss_sidebar_category_livechat_open: { default: true },
});
