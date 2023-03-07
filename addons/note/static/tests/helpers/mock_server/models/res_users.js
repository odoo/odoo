/** @odoo-module **/

// ensure mail override is applied first.
import '@mail/../tests/helpers/mock_server/models/res_users';

import { patch } from '@web/core/utils/patch';
import { MockServer } from '@web/../tests/helpers/mock_server';

patch(MockServer.prototype, 'note/models/res_users', {
    /**
     * Simulates `systray_get_activities` on `res.users`.
     *
     * @override
     */
    _mockResUsersSystrayGetActivities() {
        const activities = this._super(...arguments);
        const noteCount = this.pyEnv['project.task'].searchCount([['user_ids', 'in', [this.currentUserId]]]);
        if (noteCount) {
            const noteIndex = activities.findIndex(act => act['model'] === 'project.task');
            if (noteIndex) {
                activities[noteIndex]['name'] = 'Tasks';
            } else {
                activities.push({
                    id: 'project.task', // for simplicity
                    type: 'activity',
                    name: 'Tasks',
                    model: 'project.task',
                    planned_count: 0,
                    today_count: 0,
                    overdue_count: 0,
                    total_count: 0,
                });
            }
        }
        return activities;
    },
});
