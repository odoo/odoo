/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging';

addFields('Messaging', {
    isInPublicLivechat: attr({
        default: false,
    }),
    isPublicLivechatAvailable: attr({
        default: false,
    }),
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
    publicLivechatOptions: attr({
        default: {},
    }),
    publicLivechatServerUrl: attr({
        default: '',
    }),
});

addRecordMethods('Messaging', {
    /**
     * @private
     * @returns {FieldCommand}
     */
    _computeLivechatButtonView() {
        if (this.isInPublicLivechat && this.isPublicLivechatAvailable) {
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
        if (this.isInPublicLivechat) {
            return clear();
        }
        return this._super();
    },
});
