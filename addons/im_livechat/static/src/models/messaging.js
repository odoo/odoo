/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging';

addFields('Messaging', {
    isInPublicLivechat: attr({
        default: false,
    }),
    isPublicLivechatAvailable: attr({
        default: false,
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

patchRecordMethods('Messaging', {
     /**
     * @override
     */
    async performInitRpc() {
        if (this.isInPublicLivechat) {
            return {};
        } else {
            return this._super();
        }
    },
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
