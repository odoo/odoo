/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import '@mail/models/user_setting'; // ensure the model definition is loaded before the patch

addFields('UserSetting', {
    isDiscussSidebarCategoryLivechatOpen: attr(),
});
