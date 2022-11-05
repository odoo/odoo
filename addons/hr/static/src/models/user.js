/** @odoo-module **/

import { one, registerPatch } from '@mail/model';

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
