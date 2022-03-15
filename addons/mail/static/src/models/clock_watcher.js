/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

/**
 * Models a record that makes use of a clock.
 */
registerModel({
    name: 'ClockWatcher',
    identifyingFields: [['activityViewOwner']],
    fields: {
        activityViewOwner: one('ActivityView', {
            inverse: 'clockWatcher',
            readonly: true,
        }),
        clock: one('Clock', {
            inverse: 'watchers',
            required: true,
        }),
    },
});
