/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging';

addFields('Messaging', {
    /**
     * All pinned livechats that are known.
     */
    pinnedLivechats: many('Thread', {
        inverse: 'messagingAsPinnedLivechat',
        readonly: true,
    }),
    publicLivechatGlobal: one('PublicLivechatGlobal', {
        isCausal: true,
    }),
});

patchRecordMethods('Messaging', {
    /**
     * @override
     */
    _computeNotificationHandler() {
        if (this.publicLivechatGlobal) {
            return clear();
        }
        return this._super();
    },
});
