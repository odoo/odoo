/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/throttle';

addFields('Throttle', {
    qunitTestOwner1: one('QUnitTest', {
        identifying: true,
        inverse: 'throttle1',
        readonly: true,
    }),
    qunitTestOwner2: one('QUnitTest', {
        identifying: true,
        inverse: 'throttle2',
        readonly: true,
    }),
});

patchRecordMethods('Throttle', {
    _computeDuration() {
        if (this.qunitTestOwner1) {
            return 0;
        }
        if (this.qunitTestOwner2) {
            return 1000;
        }
        return this._super();
    },
});
