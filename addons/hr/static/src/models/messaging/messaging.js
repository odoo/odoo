odoo.define('hr/static/src/models/messaging/messaging.js', function (require) {
'use strict';

const {
    registerInstancePatchModel,
} = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.messaging', 'hr/static/src/models/messaging/messaging.js', {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {integer} [param0.employeeId]
     */
    async getChat({ employeeId }) {
        if (employeeId) {
            const employee = this.env.models['hr.employee'].insert({
                __mfield_id: employeeId,
            });
            return employee.getChat();
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async openProfile({ id, model }) {
        if (model === 'hr.employee' || model === 'hr.employee.public') {
            const employee = this.env.models['hr.employee'].insert({
                __mfield_id: id,
            });
            return employee.openProfile();
        }
        return this._super(...arguments);
    },
});

});
