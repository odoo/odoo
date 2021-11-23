/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { one2many } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging/messaging';

addFields('Messaging', {
    /**
     * All pinned livechats that are known.
     */
    pinnedLivechats: one2many('Thread', {
        inverse: 'messagingAsPinnedLivechat',
        readonly: true,
    }),
});
