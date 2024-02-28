/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerPatch({
    name: 'Chatbot',
    fields: {
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
        isWebsiteLivechatTourFlow: attr({
            default: false,
        }),
        messageDelay: {
            compute() {
                if (this.isWebsiteLivechatTourFlow) {
                    return 100;
                }
                return this._super();
            },
        },
    },
});
