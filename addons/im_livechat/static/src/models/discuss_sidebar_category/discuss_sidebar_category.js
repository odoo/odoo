/** @odoo-module **/

import { addFields, patchIdentifyingFields } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/discuss_sidebar_category/discuss_sidebar_category';

addFields('mail.discuss_sidebar_category', {
    discussAsLivechat: one2one('mail.discuss', {
        inverse: 'categoryLivechat',
        readonly: true,
    }),
});

patchIdentifyingFields('mail.discuss_sidebar_category', identifyingFields => {
    identifyingFields[0].push('discussAsLivechat');
});
