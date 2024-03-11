/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'ChatWindow',
    recordMethods: {
        /**
         * @override
         */
        close({ notifyServer } = {}) {
            if (
                this.thread &&
                this.thread.channel &&
                this.thread.channel.channel_type === 'livechat' &&
                this.thread.cache.isLoaded &&
                this.thread.messages.length === 0
            ) {
                notifyServer = true;
                this.thread.unpin();
            }
            this._super({ notifyServer });
        },
    },
});
