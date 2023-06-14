/* @odoo-module */

import {
    Messaging,
    initMessagingCallback,
    _handleNotificationLastInterestDtChanged,
    _handleNotificationRecordInsert,
} from "@mail/core/common/messaging_service";
import { sortChannels } from "@mail/core/common/thread_service";
import { createLocalId } from "@mail/utils/common/misc";
import { patchFn } from "@mail/utils/common/patch";

import { patch } from "@web/core/utils/patch";

let store;

patchFn(initMessagingCallback, function (data) {
    this._super(data);
    if (data.current_user_settings?.is_discuss_sidebar_category_livechat_open) {
        store.discuss.livechat.isOpen = true;
    }
});

patchFn(_handleNotificationRecordInsert, function (notif) {
    this._super(notif);
    const { "res.users.settings": settings } = notif.payload;
    if (settings) {
        store.discuss.livechat.isOpen =
            settings.is_discuss_sidebar_category_livechat_open ?? store.discuss.livechat.isOpen;
    }
});

patchFn(_handleNotificationLastInterestDtChanged, function (notif) {
    this._super(notif);
    const channel = store.threads[createLocalId("discuss.channel", notif.payload.id)];
    if (channel?.type === "livechat") {
        sortChannels();
    }
});

patch(Messaging.prototype, "im_livechat", {
    setup(env, services) {
        this._super(...arguments);
        store = services["mail.store"];
    },
});
