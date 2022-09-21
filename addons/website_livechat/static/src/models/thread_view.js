/** @odoo-module **/

import { addFields, addRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread_view';

addRecordMethods('ThreadView', {});

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
