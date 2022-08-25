/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure the model definition is loaded before the patch
import '@mail/models/thread_needaction_preview_view';

patchRecordMethods('ThreadNeedactionPreviewView', {
    /**
     * @override
     */
    _computeIsEmpty() {
        return this.isRating || this._super();
    },
});

addRecordMethods('ThreadNeedactionPreviewView', {
    /**
     * @private
     */
    _computeIsRating() {
        return Boolean(this.thread.lastNeedactionMessageAsOriginThread && this.thread.lastNeedactionMessageAsOriginThread.rating);
    },
});

addFields('ThreadNeedactionPreviewView', {
    isRating: attr({
        compute: '_computeIsRating',
    }),
});
