/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

/**
 * Models a record that makes use of a clock.
 */
registerModel({
    name: 'ClockWatcher',
    identifyingMode: 'xor',
    fields: {
        activityViewOwner: one('ActivityView', {
            identifying: true,
            inverse: 'clockWatcher',
        }),
        clock: one('Clock', {
            inverse: 'watchers',
            required: true,
        }),
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'clockWatcher',
        }),
    },
});
