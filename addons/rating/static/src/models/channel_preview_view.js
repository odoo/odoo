/** @odoo-module **/

import { attr, registerPatch } from '@mail/model';

registerPatch({
    name: 'ChannelPreviewView',
    fields: {
        isEmpty: {
            compute() {
                return this.isRating || this._super();
            },
        },
        isRating: attr({
            compute() {
                return Boolean(this.thread.lastMessage && this.thread.lastMessage.rating);
            },
        }),
    },
});
