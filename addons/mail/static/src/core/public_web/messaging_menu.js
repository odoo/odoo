import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { NotificationItem } from "@mail/core/public_web/notification_item";
import { useDiscussSystray } from "@mail/utils/common/hooks";

import { Component, useExternalListener, useRef, useState, useSubEnv } from "@odoo/owl";

import { hasTouch, isDisplayStandalone, isIOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { DiscussContent } from "./discuss_content";

export class MessagingMenu extends Component {
    static components = { CountryFlag, DiscussContent, Dropdown, NotificationItem, ImStatus };
    static props = [];
    static template = "mail.MessagingMenu";

    setup() {
        super.setup();
        this.isIosPwa = isIOS() && isDisplayStandalone();
        this.discussSystray = useDiscussSystray();
        this.store = useService("mail.store");
        this.hasTouch = hasTouch;
        this.ui = useService("ui");
        this.state = useState({
            activeIndex: null,
            adding: false,
        });
        this.dropdown = useDropdownState();
        this.notificationList = useRef("notification-list");
        useSubEnv({ inMessagingMenu: { dropdown: this.dropdown } });

        useExternalListener(window, "keydown", this.onKeydown, true);
    }

    onClickThread(isMarkAsRead, thread, message) {
        if (!isMarkAsRead) {
            if (message?.needaction && message.message_type === "user_notification") {
                this.store.inbox.highlightMessage = message;
                this.store.inbox.open();
                return;
            }
            thread.open({ focus: true, fromMessagingMenu: true, bypassCompact: true });
            this.dropdown.close();
            return;
        }
        this.markAsRead(thread);
    }

    onClickInboxMsg(isMarkAsRead, msg) {
        if (!isMarkAsRead) {
            this.store.inbox.highlightMessage = msg;
            this.env.services.action.doAction({
                tag: "mail.action_discuss",
                type: "ir.actions.client",
                context: { active_id: "mail.box_inbox" },
            });
            return;
        }
        msg.setDone();
    }

    markAsRead(thread) {
        if (thread.needactionMessages.length > 0) {
            thread.markAllMessagesAsRead();
        }
    }

    navigate(direction) {
        if (this.notificationItems.length === 0) {
            return;
        }
        const activeOptionId = this.state.activeIndex !== null ? this.state.activeIndex : 0;
        let targetId = undefined;
        switch (direction) {
            case "first":
                targetId = 0;
                break;
            case "last":
                targetId = this.notificationItems.length - 1;
                break;
            case "previous":
                targetId = activeOptionId - 1;
                if (targetId < 0) {
                    this.navigate("last");
                    return;
                }
                break;
            case "next":
                targetId = activeOptionId + 1;
                if (targetId > this.notificationItems.length - 1) {
                    this.navigate("first");
                    return;
                }
                break;
            default:
                return;
        }
        this.state.activeIndex = targetId;
        this.notificationItems[targetId]?.scrollIntoView({ block: "nearest" });
    }

    onKeydown(ev) {
        if (!this.dropdown.isOpen) {
            return;
        }
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
                if (this.state.activeIndex === null) {
                    return;
                }
                this.notificationItems[this.state.activeIndex].click();
                break;
            case "tab":
                this.navigate(this.state.activeIndex === null ? "first" : "next");
                break;
            case "arrowup":
                this.navigate(this.state.activeIndex === null ? "first" : "previous");
                break;
            case "arrowdown":
                this.navigate(this.state.activeIndex === null ? "first" : "next");
                break;
            default:
                return;
        }
        ev.preventDefault();
        ev.stopPropagation();
    }

    get notificationItems() {
        return this.notificationList.el?.children ?? [];
    }

    get threads() {
        return this.store.menuThreads;
    }

    get visibleStandaloneMessages() {
        const tab = this.store.discuss.activeTab;
        if (tab !== "notification") {
            return [];
        }
        if (this.store.discuss.searchTerm) {
            return [];
        }
        return this.store.standaloneInboxMessages;
    }

    /**
     * @type {{ id: string, icon: string, label: string }[]}
     */
    get _tabs() {
        return [
            {
                counter: this.store.discuss.chats.threadsWithCounter.length,
                icon: "oi oi-users",
                id: "chat",
                label: _t("Chats"),
                sequence: 20,
            },
            {
                channelHasUnread: Boolean(this.store.discuss.unreadChannels.length),
                counter: this.store.discuss.channels.threadsWithCounter.length,
                icon: "fa fa-hashtag",
                id: "channel",
                label: _t("Channels"),
                sequence: 40,
            },
        ];
    }

    get tabs() {
        return this._tabs.sort((t1, t2) => t1.sequence - t2.sequence);
    }

    onClickNavTab(tabId) {
        if (this.store.discuss.activeTab === tabId) {
            return;
        }
        this.store.discuss.activeTab = tabId;
        if (
            this.store.discuss.activeTab === "inbox" &&
            (!this.store.discuss.thread || this.store.discuss.thread.model !== "mail.box")
        ) {
            this.store.inbox.setAsDiscussThread();
        }
        if (this.store.discuss.activeTab === "starred") {
            this.store.starred.setAsDiscussThread();
        }
        if (!["inbox", "starred"].includes(this.store.discuss.activeTab)) {
            this.store.discuss.thread = undefined;
        }
    }

    canUnpinItem(thread) {
        return thread.canUnpin && thread.self_member_id?.message_unread_counter === 0;
    }
}

registry
    .category("systray")
    .add("mail.messaging_menu", { Component: MessagingMenu }, { sequence: 25 });
