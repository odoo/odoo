import { Store, StorePlugin } from "@mail/core/common/store_plugin";
import { fields, patchModel } from "@mail/model/export";
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";

export const storePatch = patchModel(Store, {
    setup() {
        super.setup(...arguments);
        this.discuss = fields.One("DiscussApp");
        this.messagingMenu = this.computed(() => this.MessagingMenu.insert({}));
        this.showPushPermissionRequest = this.computed(
            () =>
                this.env.services["mail.notification.permission"]?.permission === "prompt" &&
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
        const discussActionIds = ["mail.action_discuss", "discuss"];
        if (this.store.action_discuss_id) {
            discussActionIds.push(this.store.action_discuss_id);
        }
        this.store.discuss.isActive ||= discussActionIds.includes(router.current.action);
    },
});
