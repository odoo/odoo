/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { many } from '@mail/model/model_field';

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
