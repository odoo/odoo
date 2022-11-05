/** @odoo-module **/

import { one, registerPatch } from '@mail/model';

registerPatch({
    name: 'ClockWatcher',
    fields: {
        qunitTestOwner: one('QUnitTest', {
            identifying: true,
            inverse: 'clockWatcher',
        }),
    },
});
