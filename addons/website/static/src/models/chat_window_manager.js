/** @odoo-module **/

import { Patch } from '@mail/model';
import { BASE_VISUAL } from '@mail/models/chat_window_manager';

Patch({
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
