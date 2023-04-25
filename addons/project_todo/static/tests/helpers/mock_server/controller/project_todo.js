/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { MockServer } from '@web/../tests/helpers/mock_server';

import { date_to_str } from 'web.time';

patch(MockServer.prototype, 'project_todo/controller/project_todo', {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/project_todo/new') {
            return this._mockRouteTodoNew(args);
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Routes
    //--------------------------------------------------------------------------

    /**
     * Simulates the `/project_todo/new` route.
     *
     * @private
     */
    _mockRouteTodoNew(values) {
        const taskId = this.pyEnv['project.task'].create({ description: values['todo_description'] });
        if (values['date_deadline']) {
            this.pyEnv['mail.activity'].create({
                date_deadline: date_to_str(new Date(values['date_deadline'])),
                note: values['todo_description'],
                res_model: 'project.task',
                res_id: taskId,
            });
        }
    },
});
