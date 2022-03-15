/** @odoo-module **/

import { addFields, patchIdentifyingFields } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/message_view';

addFields('MessageView', {
    qunitTest: one('QUnitTest', {
        inverse: 'messageView',
        readonly: true,
    }),
});

patchIdentifyingFields('MessageView', identifyingFields => {
    identifyingFields[0].push('qunitTest');
});
