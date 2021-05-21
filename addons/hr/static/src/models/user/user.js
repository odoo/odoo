/** @odoo-module **/

const { one2one } = require('@mail/model/model_field');

export const fieldPatchUser = {
    /**
     * Employee related to this user.
     */
    employee: one2one('hr.employee', {
        inverse: 'user',
    }),
};
