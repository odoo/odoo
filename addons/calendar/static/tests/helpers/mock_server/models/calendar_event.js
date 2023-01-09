/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { MockServer } from '@web/../tests/helpers/mock_server';

patch(MockServer.prototype, 'calendar/models/calendar_event', {
    /**
     * @override
     */
    async _performRPC(route, args) {
        // calendar.event methods
        if (args.model === 'calendar.event' && args.method === 'check_access_rights') {
            return true;
        }
        return this._super(...arguments);
    },
});
