/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/core_models/messaging';

patchRecordMethods('Messaging', {
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
            return employee.openProfile();
        }
        return this._super(...arguments);
    },
});
