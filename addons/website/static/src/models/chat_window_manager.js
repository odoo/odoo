/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { BASE_VISUAL } from '@mail/models/chat_window_manager';

registerPatch({
    name: 'ChatWindowManager',
    fields: {
        visual: {
            compute() {
                if (this.messaging.isWebsitePreviewOpen) {
                    return JSON.parse(JSON.stringify(BASE_VISUAL));
                }
                return this._super();
            },
        },
    },
});
