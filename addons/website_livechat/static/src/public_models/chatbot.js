/** @odoo-module **/

import { addFields, patchFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@im_livechat/public_models/chatbot';

addFields('Chatbot', {
    isWebsiteLivechatTourFlow: attr({
        default: false,
    }),
});

patchFields('Chatbot', {
    awaitUserInputDebounceTime: {
        compute() {
            if (this.isWebsiteLivechatTourFlow) {
                /**
                 * Let us make it a bit faster than the default delay (3500ms).
                 * Let us also debounce waiting for more user inputs for only 500ms.
                 */
                return 500;
            }
            return this._super();
        },
    },
    messageDelay: {
        compute() {
            if (this.isWebsiteLivechatTourFlow) {
                return 100;
            }
            return this._super();
        },
    },
});


