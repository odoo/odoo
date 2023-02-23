/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { MockServer } from '@web/../tests/helpers/mock_server';

import { date_to_str } from 'web.time';

patch(MockServer.prototype, 'note/controller/note', {
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
});
