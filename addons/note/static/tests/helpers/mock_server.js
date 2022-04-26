/** @odoo-module **/

// ensure mail override is applied first.
import '@mail/../tests/helpers/mock_server';
import MockServer from 'web.MockServer';
import { date_to_str } from 'web.time';

MockServer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRpc(route, args) {
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
        const noteId = this.mockCreate('note.note', { memo: values['note'] });
        if (values['date_deadline']) {
            this.mockCreate('mail.activity', {
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
        const noteCount = this.mockSearchCount('note.note', [[['user_id', '=', this.currentUserId]]]);
        if (noteCount) {
            const noteIndex = activities.findIndex(act => act['model'] === 'note.note');
            if (noteIndex) {
                activities[noteIndex]['name'] = 'Notes';
            } else {
                activities.push({
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
