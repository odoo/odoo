/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";
import { NotificationItem } from "@mail/core/web/notification_item";
import { onExternalClick } from "@mail/utils/common/hooks";
import { createLocalId } from "@mail/utils/common/misc";

import { Component, useState } from "@odoo/owl";

import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";

export class MessagingMenu extends Component {
    static components = { Dropdown, NotificationItem, ImStatus };
    static props = [];
    static template = "mail.MessagingMenu";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.hasTouch = hasTouch;
        this.notification = useState(useService("mail.notification.permission"));
        /** @type {import("@mail/core/common/chat_window_service").ChatWindowService} */
        this.chatWindowService = useState(useService("mail.chat_window"));
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
        this.action = useService("action");
        this.ui = useState(useService("ui"));
        this.state = useState({
            addingChat: false,
            addingChannel: false,
            isOpen: false,
        });
        onExternalClick("selector", () => {
            Object.assign(this.state, { addingChat: false, addingChannel: false });
        });
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
        if (thread.hasNeedactionMessages) {
            this.threadService.markAllMessagesAsRead(thread);
        }
        if (thread.model === "discuss.channel") {
            this.threadService.markAsRead(thread);
        }
    }

    createLocalId(...args) {
        return createLocalId(...args);
    }

    /**
     * @param {'chat' | 'group'} tab
     * @returns Thread types matching the given tab.
     */
    tabToThreadType(tab) {
        return tab === "chat" ? ["chat", "group"] : [tab];
    }

    get hasPreviews() {
        return (
            this.threads.length > 0 ||
            (this.store.notificationGroups.length > 0 && this.store.discuss.activeTab === "all") ||
            (this.notification.permission === "prompt" && this.store.discuss.activeTab === "all")
        );
    }

    get notificationRequest() {
        return {
            body: _t("Enable desktop notifications to chat"),
            displayName: sprintf(_t("%s has a request"), this.store.odoobot.name),
            iconSrc: this.threadService.avatarUrl(this.store.odoobot),
            partner: this.store.odoobot,
            isLast: this.threads.length === 0 && this.store.notificationGroups.length === 0,
            isShown:
                this.store.discuss.activeTab === "all" && this.notification.permission === "prompt",
        };
    }

    get threads() {
        /** @type {import("@mail/core/common/thread_model").Thread[]} */
        let threads = Object.values(this.store.threads).filter(
            (thread) =>
                thread.is_pinned || (thread.hasNeedactionMessages && thread.type !== "mailbox")
        );
        const tab = this.store.discuss.activeTab;
        if (tab !== "all") {
            threads = threads.filter(({ type }) => this.tabToThreadType(tab).includes(type));
        }
        return threads.sort((a, b) => {
            /**
             * Ordering:
             * - threads with needaction
             * - unread channels
             * - read channels
             * - odoobot chat
             *
             * In each group, thread with most recent message comes first
             */
            if (a.correspondent === this.store.odoobot && b.correspondent !== this.store.odoobot) {
                return 1;
            }
            if (b.correspondent === this.store.odoobot && a.correspondent !== this.store.odoobot) {
                return -1;
            }
            if (a.hasNeedactionMessages && !b.hasNeedactionMessages) {
                return -1;
            }
            if (b.hasNeedactionMessages && !a.hasNeedactionMessages) {
                return 1;
            }
            if (a.message_unread_counter > 0 && b.message_unread_counter === 0) {
                return -1;
            }
            if (b.message_unread_counter > 0 && a.message_unread_counter === 0) {
                return 1;
            }
            if (!a.newestPersistentMessage?.datetime && b.newestPersistentMessage?.datetime) {
                return 1;
            }
            if (!b.newestPersistentMessage?.datetime && a.newestPersistentMessage?.datetime) {
                return -1;
            }
            if (a.newestPersistentMessage?.datetime && b.newestPersistentMessage?.datetime) {
                return b.newestPersistentMessage.datetime - a.newestPersistentMessage.datetime;
            }
            return b.localId > a.localId ? 1 : -1;
        });
    }

    /**
     * @type {{ id: string, icon: string, label: string }[]}
     */
    get tabs() {
        if (this.env.inDiscussApp) {
            return [
                {
                    icon: "fa fa-inbox",
                    id: "mailbox",
                    label: _t("Mailboxes"),
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
        } else {
            return [
                {
                    icon: "fa fa-envelope",
                    id: "all",
                    label: _t("All"),
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
    }

    openDiscussion(thread) {
        this.threadService.open(thread);
        this.close();
    }

    onClickNewMessage() {
        if (this.ui.isSmall && this.env.inDiscussApp) {
            this.state.addingChat = true;
        } else {
            this.chatWindowService.openNewMessage();
        }
        this.close();
    }

    /**
     *
     * @param {import("@mail/core/common/notification_group_model").NotificationGroup} failure
     */
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
            this.store.chatWindows.find(({ thr }) => thr === thread)?.close();
        } else {
            this.threadService.open(thread);
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
            this.store.discuss.activeTab === "mailbox" &&
            (!this.store.discuss.threadLocalId ||
                this.store.threads[this.store.discuss.threadLocalId].type !== "mailbox")
        ) {
            this.threadService.setDiscussThread(
                Object.values(this.store.threads).find((thread) => thread.id === "inbox")
            );
        }
        if (this.store.discuss.activeTab !== "mailbox") {
            this.store.discuss.threadLocalId = null;
        }
    }

    get counter() {
        let value =
            this.store.discuss.inbox.counter +
            Object.values(this.store.threads).filter(
                (thread) => thread.is_pinned && thread.message_unread_counter > 0
            ).length +
            Object.values(this.store.notificationGroups).reduce(
                (acc, ng) => acc + parseInt(Object.values(ng.notifications).length),
                0
            );
        if (this.notification.permission === "prompt") {
            value++;
        }
        return value;
    }
}

registry
    .category("systray")
    .add("mail.messaging_menu", { Component: MessagingMenu }, { sequence: 25 });
