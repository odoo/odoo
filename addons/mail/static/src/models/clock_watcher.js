/** @odoo-module **/

import { one, registerModel } from '@mail/model';

/**
 * Models a record that makes use of a clock.
 */
registerModel({
    name: 'ClockWatcher',
    identifyingMode: 'xor',
    fields: {
        activityListViewItemOwner: one('ActivityListViewItem', { identifying: true, inverse: 'clockWatcher' }),
        activityViewOwner: one('ActivityView', { identifying: true, inverse: 'clockWatcher' }),
        clock: one('Clock', { inverse: 'watchers', required: true }),
        messageViewOwner: one('MessageView', { identifying: true, inverse: 'clockWatcher' }),
    },
});
