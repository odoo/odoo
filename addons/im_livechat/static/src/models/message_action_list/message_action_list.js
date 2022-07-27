/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

registerInstancePatchModel('mail.message_action_list', 'im_livechat/static/src/models/message_action_list/message_action_list.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _computeHasReplyIcon() {
        if (
            this.message &&
            this.message.originThread &&
            this.message.originThread.channel_type === 'livechat'
        ) {
            return false;
        }
        return this._super();
    }
});
