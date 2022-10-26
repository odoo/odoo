/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'ChannelPreviewView',
    fields: {
        imageUrl: {
            compute() {
                if (this.channel.channel_type === 'livechat') {
                    return '/mail/static/src/img/smiley/avatar.jpg';
                }
                return this._super();
            },
        },
    },
});
