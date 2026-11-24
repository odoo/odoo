import { NotificationPermissionPlugin } from "@mail/core/common/notification_permission_plugin";
import { Store, StorePlugin } from "@mail/core/common/store_plugin";
import { fields } from "@mail/model/export";

import { usePlugin } from "@odoo/owl";

import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.discuss = fields.One("DiscussApp");
        this.messagingMenu = this.computed(() => this.MessagingMenu.insert({}));
        this.showPushPermissionRequest = this.computed(
            () =>
                this.notificationPermission?.permission === "prompt" &&
                !this.isNotificationPermissionDismissed
        );
    },
    onStarted() {
        super.onStarted(...arguments);
        this.discuss = {};
    },
});

patch(StorePlugin.prototype, {
    setup() {
        super.setup(...arguments);
        this.store.notificationPermission = usePlugin(NotificationPermissionPlugin);
        const discussActionIds = ["mail.action_discuss", "discuss"];
        if (this.store.action_discuss_id) {
            discussActionIds.push(this.store.action_discuss_id);
        }
        this.store.discuss.isActive ||= discussActionIds.includes(router.current.action);
    },
});
