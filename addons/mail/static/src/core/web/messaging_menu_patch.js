import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { onExternalClick } from "@mail/utils/common/hooks";
import { useEffect } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { MessagingMenuQuickSearch } from "@mail/core/web/messaging_menu_quick_search";

Object.assign(MessagingMenu.components, { MessagingMenuQuickSearch });

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
        this.pwa = useService("pwa");
        this.notification = useService("mail.notification.permission");
        Object.assign(this.state, {
            searchOpen: false,
        });

        onExternalClick("selector", () => Object.assign(this.state, { adding: false }));
        useEffect(
            () => {
                if (
                    this.store.discuss.searchTerm &&
                    this.lastSearchTerm !== this.store.discuss.searchTerm &&
                    this.state.activeIndex
                ) {
                    this.state.activeIndex = 0;
                }
                if (!this.store.discuss.searchTerm) {
                    this.state.activeIndex = null;
                }
                this.lastSearchTerm = this.store.discuss.searchTerm;
            },
            () => [this.store.discuss.searchTerm]
        );
        useEffect(
            () => {
                if (!this.dropdown.isOpen) {
                    this.state.activeIndex = null;
                }
            },
            () => [this.dropdown.isOpen]
        );
    },
    beforeOpen() {
        this.state.searchOpen = false;
        this.store.discuss.searchTerm = "";
        this.store.isReady.then(() => {
            if (
                !this.store.inbox.isLoaded &&
                this.store.inbox.status !== "loading" &&
                this.store.inbox.counter !== this.store.inbox.messages.length
            ) {
                this.store.inbox.fetchNewMessages();
            }
        });
    },
    get canPromptToInstall() {
        return this.pwa.canPromptToInstall;
    },
    get hasPreviews() {
        return (
            this.threads.length > 0 ||
            (this.store.failures.length > 0 && this.store.discuss.activeTab === "notification") ||
            (this.shouldAskPushPermission && this.store.discuss.activeTab === "notification") ||
            (this.canPromptToInstall && this.store.discuss.activeTab === "notification")
        );
    },
    get installationRequest() {
        return {
            body: _t("Come here often? Install the app for quick and easy access!"),
            displayName: _t("Install Odoo"),
            onClick: () => {
                this.pwa.show();
            },
            iconSrc: this.store.odoobot.avatarUrl,
            partner: this.store.odoobot,
            isShown: this.store.discuss.activeTab === "notification" && this.canPromptToInstall,
        };
    },
    get notificationRequest() {
        return {
            body: _t("Stay tuned! Enable push notifications to never miss a message."),
            displayName: _t("Turn on notifications"),
            iconSrc: this.store.odoobot.avatarUrl,
            partner: this.store.odoobot,
            isShown:
                this.store.discuss.activeTab === "notification" && this.shouldAskPushPermission,
        };
    },
    get _tabs() {
        return [
            {
                icon: "fa fa-envelope",
                id: "notification",
                label: _t("Notifications"),
                sequence: 10,
            },
            {
                counter:
                    this.store.self.main_user_id?.notification_type === "inbox"
                        ? this.store.inbox.counter
                        : this.store.starred.counter,
                icon:
                    this.store.self.main_user_id?.notification_type === "inbox"
                        ? "fa fa-inbox"
                        : "fa fa-star-o",
                id:
                    this.store.self.main_user_id?.notification_type === "inbox"
                        ? "inbox"
                        : "starred",
                label:
                    this.store.self.main_user_id?.notification_type === "inbox"
                        ? _t("Inbox")
                        : _t("Starred"),
                sequence: 100,
            },
            ...super._tabs,
        ];
    },
    /** @param {import("models").Failure} failure */
    onClickFailure(failure) {
        const threadIds = new Set(
            failure.notifications.map(({ mail_message_id: message }) => message.thread.id)
        );
        if (threadIds.size === 1) {
            const message = failure.notifications[0].mail_message_id;
            this.openThread(message.thread);
        } else {
            this.openFailureView(failure);
            this.dropdown.close();
        }
    },
    async openThread(thread) {
        thread.open({ focus: true, fromMessagingMenu: true });
        this.dropdown.close();
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
    toggleSearch() {
        this.store.discuss.searchTerm = "";
        this.state.searchOpen = !this.state.searchOpen;
    },
    get counter() {
        let value =
            this.store.inbox.counter +
            this.store.failures.reduce((acc, f) => acc + parseInt(f.notifications.length), 0);
        if (this.canPromptToInstall) {
            value++;
        }
        if (this.shouldAskPushPermission) {
            value++;
        }
        return value;
    },
    get shouldAskPushPermission() {
        return (
            this.notification.permission === "prompt" &&
            !this.store.isNotificationPermissionDismissed
        );
    },
    getFailureNotificationName(failure) {
        if (failure.type === "email") {
            return _t("Email Failure: %(modelName)s", { modelName: failure.modelName });
        }
        return _t("Failure: %(modelName)s", { modelName: failure.modelName });
    },
});
