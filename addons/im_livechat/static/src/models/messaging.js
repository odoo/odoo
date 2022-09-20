/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { many } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/core_models/messaging';

addFields('Messaging', {
    /**
     * All pinned livechats that are known.
     */
    pinnedLivechats: many('Thread', {
        inverse: 'messagingAsPinnedLivechat',
        readonly: true,
    }),
});
