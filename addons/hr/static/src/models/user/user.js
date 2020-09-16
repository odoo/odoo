odoo.define('hr/static/src/models/user/user.js', function (require) {
'use strict';

const {
    registerFieldPatchModel,
} = require('mail/static/src/model/model_core.js');
const { one2one } = require('mail/static/src/model/model_field_utils.js');

registerFieldPatchModel('mail.user', 'hr/static/src/models/user/user.js', {
    /**
     * Employee related to this user.
     */
    __mfield_employee: one2one('hr.employee', {
        inverse: '__mfield_user',
    }),
});

});
