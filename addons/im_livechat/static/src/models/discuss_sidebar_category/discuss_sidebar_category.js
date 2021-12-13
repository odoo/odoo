/** @odoo-module **/

import { addFields, patchIdentifyingFields } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/discuss_sidebar_category/discuss_sidebar_category';

addFields('DiscussSidebarCategory', {
    discussAsLivechat: one2one('Discuss', {
        inverse: 'categoryLivechat',
        readonly: true,
    }),
});

patchIdentifyingFields('DiscussSidebarCategory', identifyingFields => {
    identifyingFields[0].push('discussAsLivechat');
});
