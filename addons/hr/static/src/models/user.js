/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'User',
    fields: {
        /**
         * Employee related to this user.
         */
        employee: one('Employee', {
            inverse: 'user',
        }),
    },
});
