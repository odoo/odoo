/** @odoo-module **/

// ensure mail override is applied first.
import '@mail/../tests/helpers/mock_server/models/mail_activity';

import { patch } from "@web/core/utils/patch";
import { MockServer } from '@web/../tests/helpers/mock_server';

patch(MockServer.prototype, {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRPC(route, args) {
        if (args.model === 'mail.activity' && args.method === 'action_create_calendar_event') {
            return {
                type: 'ir.actions.act_window',
                name: "Meetings",
                res_model: 'calendar.event',
                view_mode: 'calendar',
                views: [[false, 'calendar']],
                target: 'current',
            };
        }
        return super._performRPC(...arguments);
    },
});
