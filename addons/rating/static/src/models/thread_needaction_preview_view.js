/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerPatch({
    name: 'ThreadNeedactionPreviewView',
    fields: {
        isEmpty: {
            compute() {
                return this.isRating || this._super();
            },
        },
        isRating: attr({
            compute() {
                return Boolean(this.thread.lastNeedactionMessageAsOriginThread && this.thread.lastNeedactionMessageAsOriginThread.rating);
            },
        }),
    },
});
