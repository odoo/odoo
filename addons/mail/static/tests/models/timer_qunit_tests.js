/** @odoo-module **/

import { addFields, patchIdentifyingFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/timer';

addFields('Timer', {
    qunitTestOwner1: one('QUnitTest', {
        inverse: 'timer1',
        readonly: true,
    }),
    qunitTestOwner2: one('QUnitTest', {
        inverse: 'timer2',
        readonly: true,
    }),
});

patchIdentifyingFields('Timer', identifyingFields => {
    identifyingFields[0].push('qunitTestOwner1');
    identifyingFields[0].push('qunitTestOwner2');
});

patchRecordMethods('Timer', {
    _computeDuration() {
        if (this.qunitTestOwner1) {
            return 0;
        }
        if (this.qunitTestOwner2) {
            return 1000 * 1000;
        }
        return this._super();
    },
});
