/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/user';

addFields('User', {
    /**
     * Employee related to this user.
     */
    employee: one('Employee', {
        inverse: 'user',
    }),
});

