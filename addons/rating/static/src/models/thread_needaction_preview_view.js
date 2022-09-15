/** @odoo-module **/

import { addFields, patchFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure the model definition is loaded before the patch
import '@mail/models/thread_needaction_preview_view';

patchFields('ThreadNeedactionPreviewView', {
    isEmpty: {
        compute() {
            return this.isRating || this._super();
        },
    },
});

addFields('ThreadNeedactionPreviewView', {
    isRating: attr({
        compute() {
            return Boolean(this.thread.lastNeedactionMessageAsOriginThread && this.thread.lastNeedactionMessageAsOriginThread.rating);
        },
    }),
});
