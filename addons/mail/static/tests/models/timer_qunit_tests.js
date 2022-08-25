/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/timer';

addFields('Timer', {
    qunitTestOwner1: one('QUnitTest', {
        identifying: true,
        inverse: 'timer1',
    }),
    qunitTestOwner2: one('QUnitTest', {
        identifying: true,
        inverse: 'timer2',
    }),
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
