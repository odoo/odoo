/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulate the creation of a custom appointment type
     * by receiving a list of slots.
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/google_calendar/sync_data') {
            return Promise.resolve({status: 'no_new_event_from_google'});
        }
        return super._performRPC(...arguments);
    },
});
