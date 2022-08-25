/** @odoo-module **/

// ensure mail override is applied first.
import '@mail/../tests/helpers/mock_server';

import { patch } from '@web/core/utils/patch';
import { MockServer } from '@web/../tests/helpers/mock_server';

import { date_to_str } from 'web.time';

patch(MockServer.prototype, 'note', {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/note/new') {
            return this._mockRouteNoteNew(args);
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Routes
    //--------------------------------------------------------------------------

    /**
     * Simulates the `/note/new` route.
     *
     * @private
     */
    _mockRouteNoteNew(values) {
        const noteId = this.pyEnv['note.note'].create({ memo: values['note'] });
        if (values['date_deadline']) {
            this.pyEnv['mail.activity'].create({
                date_deadline: date_to_str(new Date(values['date_deadline'])),
                note_id: noteId,
                res_model: 'note.note',
            });
        }
    },

    //--------------------------------------------------------------------------
    // Private Mocked Methods
    //--------------------------------------------------------------------------

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
