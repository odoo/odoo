/** @odoo-module **/

import {
    registerFieldPatchModel,
} from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerFieldPatchModel('mail.user', 'hr/static/src/models/user/user.js', {
    /**
     * Employee related to this user.
     */
    employee: one2one('hr.employee', {
        inverse: 'user',
    }),
});

