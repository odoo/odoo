/** @odoo-module **/

import { clear, registerPatch } from '@mail/model';

registerPatch({
    name: 'ComposerView',
    fields: {
        dropZoneView: {
            compute() {
                if (this.composer.thread && this.composer.thread.channel && this.composer.thread.channel.channel_type === 'livechat') {
                    return clear();
                }
                return this._super();
            },
        },
    },
});
