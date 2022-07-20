/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/channel';

patchRecordMethods('Channel', {
    /**
     * @override
     */
    _computeCorrespondent() {
        if (this.channel_type === 'livechat') {
            // livechat correspondent never changes: always the public member.
            return;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasMemberListFeature() {
        return this.channel_type === 'livechat' || this._super();
    },
    /**
     * @override
     */
    _computeIsChat() {
        return this.channel_type === 'livechat' || this._super();
    },
    /**
     * @override
     */
    _getDiscussSidebarCategory() {
        if (this.channel_type === 'livechat') {
            return this.messaging.discuss.categoryLivechat;
        }
        return this._super();
    }
});
