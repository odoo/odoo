/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

// dummy import to ensure mail Messaging patches are loaded beforehand
import '@mail/models/messaging';

registerPatch({
    name: 'Messaging',
    recordMethods: {
        /**
         * @override
         * @param {integer} [param0.employeeId]
         */
        async getChat({ employeeId }) {
            if (employeeId) {
                const employee = this.messaging.models['Employee'].insert({ id: employeeId });
                return employee.getChat();
            }
            return this._super(...arguments);
        },
        /**
         * @override
         */
        async openProfile({ id, model }) {
            if (model === 'hr.employee' || model === 'hr.employee.public') {
                const employee = this.messaging.models['Employee'].insert({ id });
                return employee.openProfile(model);
            }
            return this._super(...arguments);
        },
    },
});
