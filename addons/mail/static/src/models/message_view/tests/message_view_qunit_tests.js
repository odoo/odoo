/** @odoo-module **/

import { addFields, patchIdentifyingFields } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/message_view/message_view';

addFields('mail.message_view', {
    qunitTest: one2one('mail.qunit_test', {
        inverse: 'messageView',
        readonly: true,
    }),
});

patchIdentifyingFields('mail.message_view', identifyingFields => {
    identifyingFields[0].push('qunitTest');
});
