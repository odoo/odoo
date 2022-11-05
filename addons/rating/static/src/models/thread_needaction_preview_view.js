/** @odoo-module **/

import { attr, registerPatch } from '@mail/model';

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
