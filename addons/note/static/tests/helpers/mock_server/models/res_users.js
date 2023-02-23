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
        const noteCount = this.pyEnv['note.note'].searchCount([['user_id', '=', this.currentUserId]]);
        if (noteCount) {
            const noteIndex = activities.findIndex(act => act['model'] === 'note.note');
            if (noteIndex) {
                activities[noteIndex]['name'] = 'Notes';
            } else {
                activities.push({
                    id: 'note.note', // for simplicity
                    type: 'activity',
                    name: 'Notes',
                    model: 'note.note',
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
