odoo.define('hr/static/src/models/user/user.js', function (require) {
'use strict';

const {
    registerFieldPatchModel,
} = require('@mail/model/model_core');
const { one2one } = require('@mail/model/model_field');

registerFieldPatchModel('mail.user', 'hr/static/src/models/user/user.js', {
    /**
     * Employee related to this user.
     */
    employee: one2one('hr.employee', {
        inverse: 'user',
    }),
});

});
