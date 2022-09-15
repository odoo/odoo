/** @odoo-module **/

import { patchFields } from '@mail/model/model_core';
import '@mail/models/notification_list_view'; // ensure the model definition is loaded before the patch

patchFields('NotificationListView', {
    filteredChannels: {
        compute() {
            if (this.filter === 'livechat') {
                return this.messaging.models['Channel'].all(channel =>
                    channel.channel_type === 'livechat' &&
                    channel.thread.isPinned
                );
            }
            return this._super();
        },
    },
});
