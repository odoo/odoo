/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread_view';

addFields('ThreadView', {
    /**
     * Determines whether visitor banner should be displayed.
     */
    hasVisitorBanner: attr({
        compute() {
            return Boolean(this.thread && this.thread.visitor && this.threadViewer && this.threadViewer.discuss);
        },
    }),
});
