/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'QUnitTest',
    fields: {
        clockWatcher: one('ClockWatcher', {
            inverse: 'qunitTestOwner',
        }),
        throttle1: one('Throttle', {
            inverse: 'qunitTestOwner1',
        }),
        throttle2: one('Throttle', {
            inverse: 'qunitTestOwner2',
        }),
        timer1: one('Timer', {
            inverse: 'qunitTestOwner1',
        }),
        timer2: one('Timer', {
            inverse: 'qunitTestOwner2',
        }),
    },
});
