/** @odoo-module **/

import { addFields, patchIdentifyingFields } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/clock_watcher/clock_watcher';

patchIdentifyingFields('ClockWatcher', identifyingFields => {
    identifyingFields[0].push('qunitTestOwner');
});

addFields('ClockWatcher', {
    qunitTestOwner: one('QUnitTest', {
        inverse: 'clockWatcher',
        readonly: true,
    }),
});
