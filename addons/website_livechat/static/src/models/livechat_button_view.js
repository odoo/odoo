/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@im_livechat/models/livechat_button_view';

patchRecordMethods('LivechatButtonView', {
   /**
     * @private
     * @returns {string}
     */
    _computeInputPlaceholder() {
        if (this.env.messaging.isPublicLivechatChatbot) {
            // void the default livechat placeholder in the user input
            // as we use it for specific things (e.g: showing "please select an option above")
            return "";
        }
        return this._super();
    },
});
