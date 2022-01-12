/** @odoo-module **/

import { addFields, addRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread_view/thread_view';

addRecordMethods('ThreadView', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @private
     * @returns {boolean}
     */
    _computeHasVisitorBanner() {
        return Boolean(this.thread && this.thread.visitor && this.threadViewer && this.threadViewer.discuss);
    },
});

addFields('ThreadView', {
    /**
     * Determines whether visitor banner should be displayed.
     */
    hasVisitorBanner: attr({
        compute: '_computeHasVisitorBanner',
    }),
});
