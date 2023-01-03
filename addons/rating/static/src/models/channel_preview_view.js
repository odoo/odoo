/** @odoo-module **/

import { attr, Patch } from '@mail/model';

Patch({
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
