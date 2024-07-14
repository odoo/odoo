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
        if (args.model === 'approval.approver' && args.method === 'action_approve') {
            const ids = args.args[0];
            return this._mockApprovalApproverActionApprove(ids);
        }
        if (args.model === 'approval.approver' && args.method === 'action_refuse') {
            const ids = args.args[0];
            return this._mockApprovalApproverActionApprove(ids);
        }
        return super._performRPC(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Methods
    //--------------------------------------------------------------------------

    /**
     * Simulates `action_approve` on `approval.approver`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockApprovalApproverActionApprove(ids) {
        // TODO implement this mock and improve related tests (task-2300537)
    },
    /**
     * Simulates `action_refuse` on `approval.approver`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockApprovalApproverActionRefuse(ids) {
        // TODO implement this mock and improve related tests (task-2300537)
    },
});
