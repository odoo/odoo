/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerPatch({
    name: 'ThreadView',
    fields: {
        /**
         * Determines whether visitor banner should be displayed.
         */
        hasVisitorBanner: attr({
            compute() {
                return Boolean(this.thread && this.thread.visitor && this.threadViewer && this.threadViewer.discuss);
            },
        }),
    },
});
