/** @odoo-module **/

import { attr, registerPatch } from '@mail/model';

registerPatch({
    name: 'Partner',
    fields: {
        /**
         * States the specific name of this partner in the context of livechat.
         * Either a string or undefined.
         */
        user_livechat_username: attr(),
    },
});
