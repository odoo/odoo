import { NotificationItem } from "@mail/core/public_web/notification_item";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { hasTouch } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(MessagingMenu.components, { NotificationItem });

patch(MessagingMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("mail.notification.permission");
        this.hasTouch = hasTouch;
    },
    /**
     * Whether the OdooBot extras (delivery failures, push permission request) may be
     * shown for the active tab.
     */
    get showNotificationHubExtras() {
        const menu = this.store.messagingMenu;
        return !this.searchTerm() && this.state().activeTab.eq(menu.odooBotNotificationsTab);
    },
    get showFailures() {
        return this.store.failures.length > 0 && this.showNotificationHubExtras;
    },
    get isEmpty() {
        return super.isEmpty && !this.showFailures && !this.showPushPermissionRequest;
    },
    get showPushPermissionRequest() {
        return this.store.showPushPermissionRequest && this.showNotificationHubExtras;
    },
    get notificationRequest() {
        return {
            body: _t("Stay tuned! Enable push notifications to never miss a message."),
            displayName: _t("Turn on notifications"),
            partner: this.store.odoobot,
        };
    },
    onClickFailure(failure) {
        const threadIds = new Set(
            failure.notifications.map(({ mail_message_id: message }) => message.thread.id)
        );
        if (threadIds.size === 1) {
            const message = failure.notifications[0].mail_message_id;
            this.openThread(message.thread);
        } else {
            this.openFailureView(failure);
            this.close?.();
        }
    },
    async openThread(thread) {
        thread.open({ focus: true, fromMessagingMenu: true });
        this.close?.();
    },
    openFailureView(failure) {
        if (failure.type !== "email") {
            return;
        }
        this.action.doAction({
            name: _t("Mail Failures"),
            type: "ir.actions.act_window",
            view_mode: "kanban,list,form",
            views: [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
            res_model: failure.resModel,
            domain: [["message_has_error", "=", true]],
            context: { create: false },
        });
    },
    cancelNotifications(failure) {
        return this.env.services.orm.call(failure.resModel, "notify_cancel_by_type", [], {
            notification_type: failure.type,
        });
    },
    getFailureNotificationName(failure) {
        if (failure.type === "email") {
            return _t("Email Failure: %(modelName)s", { modelName: failure.modelName });
        }
        return _t("Failure: %(modelName)s", { modelName: failure.modelName });
    },
});
