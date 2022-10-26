/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'ClockWatcher',
    fields: {
        qunitTestOwner: one('QUnitTest', {
            identifying: true,
            inverse: 'clockWatcher',
        }),
    },
});
