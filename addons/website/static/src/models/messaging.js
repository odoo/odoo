/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerPatch({
    name: 'Messaging',
    fields: {
        isWebsitePreviewOpen: attr({
            default: false,
        }),
    },
});
