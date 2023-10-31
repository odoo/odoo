/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerInstancePatchModel,
} from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerInstancePatchModel('mail.thread_view', 'website_livechat/static/src/models/thread_view/thread_view.js', {

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

registerFieldPatchModel('mail.thread_view', 'website_livechat/static/src/models/thread_view/thread_view.js', {
    /**
     * Determines whether visitor banner should be displayed.
     */
    hasVisitorBanner: attr({
        compute: '_computeHasVisitorBanner',
    }),
});
