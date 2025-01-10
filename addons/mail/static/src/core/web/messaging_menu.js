import { ImStatus } from "@mail/core/common/im_status";
import { NotificationItem } from "@mail/core/web/notification_item";
import { onExternalClick, useDiscussSystray } from "@mail/utils/common/hooks";

import { Component, useState } from "@odoo/owl";

import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenu extends Component {
    static components = { Dropdown, NotificationItem, ImStatus };
    static props = [];
    static template = "mail.MessagingMenu";

    setup() {
        this.discussSystray = useDiscussSystray();
        this.store = useState(useService("mail.store"));
        this.hasTouch = hasTouch;
        this.messagingService = useState(useService("mail.messaging"));
        this.notification = useState(useService("mail.notification.permission"));
        this.chatWindowService = useState(useService("mail.chat_window"));
        this.threadService = useState(useService("mail.thread"));
        this.action = useService("action");
        this.installPrompt = useState(useService("installPrompt"));
        this.ui = useState(useService("ui"));
        this.state = useState({ adding: false });
        this.dropdown = useDropdownState();

        onExternalClick("selector", () => Object.assign(this.state, { adding: false }));
    }

    beforeOpen() {
        this.messagingService.isReady.then(() => {
            if (
                !this.store.discuss.inbox.isLoaded &&
                this.store.discuss.inbox.status !== "loading" &&
                this.store.discuss.inbox.counter !== this.store.discuss.inbox.messages.length
            ) {
                this.threadService.fetchNewMessages(this.store.discuss.inbox);
            }
        });
    }

    onClickThread(isMarkAsRead, thread) {
        if (!isMarkAsRead) {
            this.openDiscussion(thread);
            return;
        }
        this.markAsRead(thread);
    }

    markAsRead(thread) {
        if (thread.needactionMessages.length > 0) {
            this.threadService.markAllMessagesAsRead(thread);
        }
        if (thread.model === "discuss.channel") {
            this.threadService.markAsRead(thread);
        }
    }

    get canPromptToInstall() {
        return this.installPrompt.canPromptToInstall;
    }

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
    }

    get installationRequest() {
        return {
            body: _t("Come here often? Install Odoo on your device!"),
            displayName: _t("%s has a suggestion", this.store.odoobot.name),
            onClick: () => {
                this.installPrompt.show();
            },
            iconSrc: this.store.odoobot.avatarUrl,
            partner: this.store.odoobot,
            isShown: this.store.discuss.activeTab === "main" && this.canPromptToInstall,
        };
    }

    get notificationRequest() {
        return {
            body: _t("Enable desktop notifications to chat"),
            displayName: _t("%s has a request", this.store.odoobot.name),
            iconSrc: this.store.odoobot.avatarUrl,
            partner: this.store.odoobot,
            isShown: this.store.discuss.activeTab === "main" && this.shouldAskPushPermission,
        };
    }

    get threads() {
        return this.store.menuThreads;
    }

    /**
     * @type {{ id: string, icon: string, label: string }[]}
     */
    get tabs() {
        return [
            {
                icon: this.env.inDiscussApp ? "fa fa-inbox" : "fa fa-envelope",
                id: "main",
                label: this.env.inDiscussApp ? _t("Mailboxes") : _t("All"),
            },
            {
                icon: "fa fa-user",
                id: "chat",
                label: _t("Chat"),
            },
            {
                icon: "fa fa-users",
                id: "channel",
                label: _t("Channel"),
            },
        ];
    }

    openDiscussion(thread) {
        this.threadService.open(thread, undefined, { openMessagingMenuOnClose: true });
        this.dropdown.close();
    }

    onClickNewMessage() {
        if (this.ui.isSmall || this.env.inDiscussApp) {
            Object.assign(this.state, { adding: "chat" });
        } else {
            this.chatWindowService.openNewMessage({ openMessagingMenuOnClose: true });
            this.dropdown.close();
        }
    }

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
    }

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
            this.store.discuss.chatWindows.find(({ thr }) => thr?.eq(thread))?.close();
        } else {
            this.threadService.open(thread, undefined, { openMessagingMenuOnClose: true });
        }
        this.dropdown.close();
    }

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
    }

    cancelNotifications(failure) {
        return this.env.services.orm.call(failure.resModel, "notify_cancel_by_type", [], {
            notification_type: failure.type,
        });
    }

    onClickNavTab(tabId) {
        if (this.store.discuss.activeTab === tabId) {
            return;
        }
        this.store.discuss.activeTab = tabId;
        if (
            this.store.discuss.activeTab === "main" &&
            this.env.inDiscussApp &&
            (!this.store.discuss.thread || this.store.discuss.thread.model !== "mail.box")
        ) {
            this.threadService.setDiscussThread(
                Object.values(this.store.Thread.records).find((thread) => thread.id === "inbox")
            );
        }
        if (this.store.discuss.activeTab !== "main") {
            this.store.discuss.thread = undefined;
        }
    }

    get counter() {
        let value =
            this.store.discuss.inbox.counter +
            this.store.failures.reduce((acc, f) => acc + parseInt(f.notifications.length), 0);
        if (this.canPromptToInstall) {
            value++;
        }
        if (this.shouldAskPushPermission) {
            value++;
        }
        return value;
    }

    get displayStartConversation() {
        return this.store.discuss.activeTab !== "channel" && !this.state.adding;
    }

    get shouldAskPushPermission() {
        return this.notification.permission === "prompt";
    }
}

registry
    .category("systray")
    .add("mail.messaging_menu", { Component: MessagingMenu }, { sequence: 25 });
