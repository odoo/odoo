/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@im_livechat/models/chatbot';

addFields('Chatbot', {
    isWebsiteLivechatTourFlow: attr({
        default: false,
    }),
});

patchRecordMethods('Chatbot', {
    /**
     * @private
     * @returns {integer|FieldCommand}
    */
    _computeMessageDelay() {
        if (this.isWebsiteLivechatTourFlow) {
            return 100;
        }
        return this._super();
    },
});


