/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { replace } from '@mail/model/model_field_command';
import '@mail/models/notification_list_view/notification_list_view'; // ensure the model definition is loaded before the patch

patchRecordMethods('NotificationListView', {
    /**
     * @override
     */
    _computeFilteredThreads() {
        if (this.filter === 'livechat') {
            return replace(this.messaging.models['Thread'].all(thread =>
                thread.channel_type === 'livechat' &&
                thread.isPinned &&
                thread.model === 'mail.channel'
            ));
        }
        return this._super();
    },
});
