import { patch } from "@web/core/utils/patch";
import { MockServer } from '@web/../tests/helpers/mock_server';

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _performRPC(route, args) {
        // calendar.event methods
        if (args.model === 'calendar.event' && args.method === 'has_access') {
            return true;
        }
        return super._performRPC(...arguments);
    },
});
