/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { NotificationItem } from "@mail/core/web/notification_item";
import { onExternalClick, useDiscussSystray } from "@mail/utils/common/hooks";

import { Component, useState } from "@odoo/owl";

import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
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
        this.notification = useState(useService("mail.notification.permission"));
        this.chatWindowService = useState(useService("mail.chat_window"));
        this.threadService = useState(useService("mail.thread"));
        this.action = useService("action");
        this.installPrompt = useState(useService("installPrompt"));
        this.ui = useState(useService("ui"));
        this.state = useState({
            addingChat: false,
            addingChannel: false,
            isOpen: false,
        });
        onExternalClick("selector", this.handleExternalClick.bind(this));
    }

    beforeOpen() {
        this.threadService.fetchPreviews();
        if (
            !this.store.discuss.inbox.isLoaded &&
            this.store.discuss.inbox.status !== "loading" &&
            this.store.discuss.inbox.counter !== this.store.discuss.inbox.messages.length
        ) {
            this.threadService.fetchNewMessages(this.store.discuss.inbox);
        }
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

    /**
     * @deprecated
     * @param {'chat' | 'group'} tab
     * @returns Thread types matching the given tab.
     */
    tabToThreadType(tab) {
        return this.store.tabToThreadType(tab);
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
            (this.store.odoobot &&
                this.notification.permission === "prompt" &&
                this.store.discuss.activeTab === "main" &&
                !this.env.inDiscussApp) ||
            (this.store.odoobot &&
                this.canPromptToInstall &&
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
            iconSrc: this.threadService.avatarUrl(this.store.odoobot),
            partner: this.store.odoobot,
            isShown: this.store.discuss.activeTab === "main" && this.canPromptToInstall,
        };
    }

    get notificationRequest() {
        return {
            body: _t("Enable desktop notifications to chat"),
            displayName: _t("%s has a request", this.store.odoobot.name),
            iconSrc: this.threadService.avatarUrl(this.store.odoobot),
            partner: this.store.odoobot,
            isShown:
                this.store.discuss.activeTab === "main" &&
                this.notification.permission === "prompt",
        };
    }

    get threads() {
        return this.getThreads();
    }

    getThreads() {
        return this.store.menuThreads;
    }

    handleExternalClick() {
        Object.assign(this.state, { addingChat: false, addingChannel: false });
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
        this.close();
    }

    onClickNewMessage() {
        if (this.ui.isSmall || this.env.inDiscussApp) {
            this.state.addingChat = true;
        } else {
            this.chatWindowService.openNewMessage({ openMessagingMenuOnClose: true });
            this.close();
        }
    }

    /** @param {import("models").Failure} failure */
    onClickFailure(failure) {
        const originThreadIds = new Set(
            failure.notifications.map(({ message }) => message.originThread.id)
        );
        if (originThreadIds.size === 1) {
            const message = failure.notifications[0].message;
            this.openThread(message.originThread);
        } else {
            this.openFailureView(failure);
            this.close();
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
        this.close();
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

    close() {
        // hack: click on window to close dropdown, because we use a dropdown
        // without dropdownitem...
        document.body.click();
    }

    onClickNavTab(tabId) {
        if (this.store.discuss.activeTab === tabId) {
            return;
        }
        this.store.discuss.activeTab = tabId;
        if (
            this.store.discuss.activeTab === "main" &&
            this.env.inDiscussApp &&
            (!this.store.discuss.thread || this.store.discuss.thread.type !== "mailbox")
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
            Object.values(this.store.Thread.records).filter(
                (thread) => thread.is_pinned && thread.message_unread_counter > 0
            ).length +
            this.store.failures.reduce((acc, f) => acc + parseInt(f.notifications.length), 0);
        if (this.canPromptToInstall) {
            value++;
        }
        if (this.notification.permission === "prompt") {
            value++;
        }
        return value;
    }

    get displayChannelSelector() {
        return this.state.addingChannel || this.state.addingChat;
    }

    get displayStartConversation() {
        return (
            !this.ui.isSmall ||
            (this.ui.isSmall &&
                this.store.discuss.activeTab !== "channel" &&
                !this.state.addingChat &&
                !(this.env.inDiscussApp && this.store.discuss.activeTab === "main"))
        );
    }
}

registry
    .category("systray")
    .add("mail.messaging_menu", { Component: MessagingMenu }, { sequence: 25 });
