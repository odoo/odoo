/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/clock_watcher';

addFields('ClockWatcher', {
    qunitTestOwner: one('QUnitTest', {
        identifying: true,
        inverse: 'clockWatcher',
        readonly: true,
    }),
});
