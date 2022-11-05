/** @odoo-module **/

import { attr, registerPatch } from '@mail/model';

registerPatch({
    name: 'Messaging',
    fields: {
        isWebsitePreviewOpen: attr({
            default: false,
        }),
    },
});
