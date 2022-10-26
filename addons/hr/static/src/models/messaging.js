/** @odoo-module **/

import { Patch } from '@mail/model';

// dummy import to ensure mail Messaging patches are loaded beforehand
import '@mail/models/messaging';

Patch({
    name: 'Messaging',
    recordMethods: {
        /**
         * @override
         * @param {integer} [param0.employeeId]
         */
        async getSyncedPersona(person) {
            const { employeeId } = person;
            if (employeeId) {
                const employee = this.models['Employee'].insert({ id: employeeId });
                if (!employee.partner) {
                    await employee.checkIsUser();
                }
                if (employee.exists() && employee.partner) {
                    return this.models['Persona'].insert({ partner: employee.partner });
                }
            }
            return this._super(person);
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
