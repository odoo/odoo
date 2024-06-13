/** @odoo-module **/

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
        if (args.model === 'project.task' && args.method === 'get_todo_views_id') {
            return [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
                [false, "activity"],
            ];
        }
        return super._performRPC(...arguments);
    },
});
