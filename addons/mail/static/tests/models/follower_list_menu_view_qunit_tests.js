/** @odoo-module **/

import { addFields, patchIdentifyingFields } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/follower_list_menu_view';

addFields('FollowerListMenuView', {
    qunitTest: one('QUnitTest', {
        inverse: 'followerListMenuView',
        readonly: true,
    }),
});

patchIdentifyingFields('FollowerListMenuView', identifyingFields => {
    identifyingFields[0].push('qunitTest');
});
