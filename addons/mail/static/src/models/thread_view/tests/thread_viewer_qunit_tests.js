/** @odoo-module **/

import { addFields, patchIdentifyingFields } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread_view/thread_viewer';

addFields('ThreadViewer', {
    qunitTest: one2one('QUnitTest', {
        inverse: 'threadViewer',
        readonly: true,
    }),
});

patchIdentifyingFields('ThreadViewer', identifyingFields => {
    identifyingFields[0].push('qunitTest');
});
