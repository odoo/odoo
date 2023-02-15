/** @odoo-module **/

import { attr, Patch } from '@mail/model';

Patch({
    name: 'Messaging',
    fields: {
        isWebsitePreviewOpen: attr({
            default: false,
        }),
    },
});
