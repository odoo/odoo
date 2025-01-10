import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { onExternalClick } from "@mail/utils/common/hooks";
import { useEffect, useState } from "@odoo/owl";

<<<<<<< 18.0:addons/mail/static/src/core/web/messaging_menu_patch.js
||||||| d8fa043f085ee1e1d11708e2bd1213b7ce3c9dd9:addons/mail/static/src/core/web/messaging_menu.js
import { Component, useState } from "@odoo/owl";

import { hasTouch, isDisplayStandalone, isIOS, isIosApp } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
=======
import { Component, useState } from "@odoo/owl";

import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
>>>>>>> b2bc9d095b338f1cb7f08a18b479af9faf8728e1:addons/mail/static/src/core/web/messaging_menu.js
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { MessagingMenuQuickSearch } from "@mail/core/web/messaging_menu_quick_search";

Object.assign(MessagingMenu.components, { MessagingMenuQuickSearch });

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
        this.pwa = useState(useService("pwa"));
        this.notification = useState(useService("mail.notification.permission"));
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
            (this.store.failures.length > 0 &&
                this.store.discuss.activeTab === "main" &&
                !this.env.inDiscussApp) ||
            (this.shouldAskPushPermission &&
                this.store.discuss.activeTab === "main" &&
                !this.env.inDiscussApp) ||
            (this.canPromptToInstall &&
                this.store.discuss.activeTab === "main" &&
                !this.env.inDiscussApp)
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
            isShown: this.store.discuss.activeTab === "main" && this.canPromptToInstall,
        };
    },
    get notificationRequest() {
        return {
            body: _t("Stay tuned! Enable push notifications to never miss a message."),
            displayName: _t("Turn on notifications"),
            iconSrc: this.store.odoobot.avatarUrl,
            partner: this.store.odoobot,
            isShown:
                this.store.discuss.activeTab === "main" &&
                this.shouldAskPushPermission &&
                !this.store.isNotificationPermissionDismissed,
        };
    },
    get tabs() {
        return [
            {
                icon: this.env.inDiscussApp ? "fa fa-inbox" : "fa fa-envelope",
                id: "main",
                label: this.env.inDiscussApp ? _t("Mailboxes") : _t("All"),
            },
            ...super.tabs,
        ];
    },
    /** @param {import("models").Failure} failure */
    onClickFailure(failure) {
        const threadIds = new Set(failure.notifications.map(({ message }) => message.thread.id));
        if (threadIds.size === 1) {
            const message = failure.notifications[0].message;
            this.openThread(message.thread);
        } else {
            this.openFailureView(failure);
            this.dropdown.close();
        }
    },
    openThread(thread) {
        if (this.store.discuss.isActive) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: thread.model,
                views: [[false, "form"]],
                res_id: thread.id,
            });
            // Close the related chat window as having both the form view
            // and the chat window does not look good.
            this.store.ChatWindow.get({ thread })?.close();
        } else {
            thread.open({ fromMessagingMenu: true });
        }
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
    get displayStartConversation() {
        return this.store.discuss.activeTab !== "channel" && !this.state.adding;
    },
    get shouldAskPushPermission() {
        return this.notification.permission === "prompt";
    },
    getFailureNotificationName(failure) {
        if (failure.type === "email") {
            return _t("Email Failure: %(modelName)s", { modelName: failure.modelName });
        }
        return _t("Failure: %(modelName)s", { modelName: failure.modelName });
    },
});
