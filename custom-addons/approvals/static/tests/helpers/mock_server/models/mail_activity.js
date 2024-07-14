/** @odoo-module **/

// ensure mail override is applied first.
import '@mail/../tests/helpers/mock_server/models/mail_activity';

import { patch } from "@web/core/utils/patch";
import { MockServer } from '@web/../tests/helpers/mock_server';

patch(MockServer.prototype, {
    /**
     * @override
     */
    _mockMailActivityActivityFormat(ids) {
        const activities = super._mockMailActivityActivityFormat(ids);
        for (const activity of activities) {
            if (activity.res_model === 'approval.request') {
                // check on activity type being approval not done here for simplicity
                const approver = this.getRecords('approval.approver', [
                    ['request_id', '=', activity.res_id],
                    ['user_id', '=', activity.user_id[0]],
                ])[0];
                if (approver) {
                    activity.approver_id = approver.id;
                    activity.approver_status = approver.status;
                }
            }
        }
        return activities;
    },
});

