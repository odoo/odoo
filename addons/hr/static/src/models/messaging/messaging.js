/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging/messaging';

patchRecordMethods('mail.messaging', {
    /**
     * @override
     * @param {integer} [param0.employeeId]
     */
    async getChat({ employeeId }) {
        if (employeeId) {
            const employee = this.messaging.models['hr.employee'].insert({ id: employeeId });
            return employee.getChat();
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async openProfile({ id, model }) {
        if (model === 'hr.employee' || model === 'hr.employee.public') {
            const employee = this.messaging.models['hr.employee'].insert({ id });
            return employee.openProfile();
        }
        return this._super(...arguments);
    },
});
