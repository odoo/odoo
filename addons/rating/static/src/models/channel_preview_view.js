/** @odoo-module **/

import { addFields, patchFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure the model definition is loaded before the patch
import '@mail/models/channel_preview_view';

patchFields('ChannelPreviewView', {
    isEmpty: {
        compute() {
            return this.isRating || this._super();
        },
    },
});

addFields('ChannelPreviewView', {
    isRating: attr({
        compute() {
            return Boolean(this.thread.lastMessage && this.thread.lastMessage.rating);
        },
    }),
});
