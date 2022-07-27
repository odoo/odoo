/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'QUnitTest',
    identifyingFields: [], // singleton acceptable (only one test at a time)
    fields: {
        clockWatcher: one('ClockWatcher', {
            inverse: 'qunitTestOwner',
            isCausal: true,
        }),
        throttle1: one('Throttle', {
            inverse: 'qunitTestOwner1',
            isCausal: true,
        }),
        throttle2: one('Throttle', {
            inverse: 'qunitTestOwner2',
            isCausal: true,
        }),
        timer1: one('Timer', {
            inverse: 'qunitTestOwner1',
            isCausal: true,
        }),
        timer2: one('Timer', {
            inverse: 'qunitTestOwner2',
            isCausal: true,
        }),
    },
});
