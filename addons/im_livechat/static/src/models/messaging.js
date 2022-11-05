/** @odoo-module **/

import { many, registerPatch } from '@mail/model';

registerPatch({
    name: 'Messaging',
    fields: {
        /**
         * All pinned livechats that are known.
         */
        pinnedLivechats: many('Thread', {
            inverse: 'messagingAsPinnedLivechat',
            readonly: true,
        }),
    },
});
