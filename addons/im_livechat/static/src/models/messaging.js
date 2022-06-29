/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging';

addFields('Messaging', {
    livechatButtonView: one('LivechatButtonView', {
        compute: '_computeLivechatButtonView',
        isCausal: true,
    }),
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

addRecordMethods('Messaging', {
    /**
     * @private
     * @returns {FieldCommand}
     */
    _computeLivechatButtonView() {
        if (this.publicLivechatGlobal && this.publicLivechatGlobal.isAvailable) {
            return insertAndReplace();
        }
        return clear();
    },
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
