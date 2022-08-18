/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure the model definition is loaded before the patch
import '@mail/models/thread_preview_view';

patchRecordMethods('ThreadPreviewView', {
    /**
     * @override
     */
    _computeIsEmpty() {
        return this.isRating || this._super();
    },
});

addRecordMethods('ThreadPreviewView', {
    /**
     * @private
     */
    _computeIsRating() {
        return Boolean(this.thread.lastMessage && this.thread.lastMessage.rating);
    },
});

addFields('ThreadPreviewView', {
    isRating: attr({
        compute: '_computeIsRating',
    }),
});
