import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { NotificationItem } from "@mail/core/public_web/notification_item";
import { useDiscussSystray } from "@mail/utils/common/hooks";

import { Component, useExternalListener, useRef, useState } from "@odoo/owl";

import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class MessagingMenu extends Component {
    static components = { CountryFlag, Dropdown, NotificationItem, ImStatus };
    static props = [];
    static template = "mail.MessagingMenu";

    setup() {
        super.setup();
        this.discussSystray = useDiscussSystray();
        this.store = useState(useService("mail.store"));
        this.hasTouch = hasTouch;
        this.ui = useState(useService("ui"));
        this.state = useState({
            activeIndex: null,
            adding: false,
        });
        this.dropdown = useDropdownState();
        this.notificationList = useRef("notification-list");

        useExternalListener(window, "keydown", this.onKeydown, true);
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
            thread.markAllMessagesAsRead();
        }
        if (thread.model === "discuss.channel") {
            thread.markAsRead();
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

    /**
     * @type {{ id: string, icon: string, label: string }[]}
     */
    get tabs() {
        return [
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
        thread.open({ fromMessagingMenu: true });
        this.dropdown.close();
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
            this.store.inbox.setAsDiscussThread();
        }
        if (this.store.discuss.activeTab !== "main") {
            this.store.discuss.thread = undefined;
        }
    }
}

registry
    .category("systray")
    .add("mail.messaging_menu", { Component: MessagingMenu }, { sequence: 25 });
