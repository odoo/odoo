import { ActionList } from "@mail/core/common/action_list";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { Thread } from "@mail/core/common/thread";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { CountryFlag } from "@mail/core/common/country_flag";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { useHover, useMessageScrolling } from "@mail/utils/common/hooks";
import { isEventHandled } from "@web/core/utils/misc";

import { Component, toRaw, useChildSubEnv, useRef, useState, useSubEnv } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Typing } from "@mail/discuss/typing/common/typing";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { isMobileOS } from "@web/core/browser/feature_detection";

/**
 * @typedef {Object} Props
 * @property {import("models").ChatWindow} chatWindow
 * @property {boolean} [right]
 * @extends {Component<Props, Env>}
 */
export class ChatWindow extends Component {
    static components = {
        ActionList,
        CountryFlag,
        Dropdown,
        Thread,
        Composer,
        ThreadIcon,
        ImStatus,
        AutoresizeInput,
        Typing,
    };
    static props = ["chatWindow", "right?"];
    static template = "mail.ChatWindow";

    setup() {
        super.setup();
        useSubEnv({ inChatWindow: true });
        this.store = useService("mail.store");
        this.messageHighlight = useMessageScrolling();
        this.state = useState({
            actionsMenuOpened: false,
            jumpThreadPresent: 0,
            editingGuestName: false,
            editingName: false,
        });
        this.ui = useService("ui");
        this.contentRef = useRef("content");
        this.threadActions = useThreadActions({ thread: () => this.thread });
        this.actionsMenuButtonHover = useHover("actionsMenuButton");
        this.parentChannelHover = useHover("parentChannel");
        this.isMobileOS = isMobileOS();

        useChildSubEnv({
            closeActionPanel: () => this.threadActions.activeAction?.close(),
            messageHighlight: this.messageHighlight,
        });
    }

    get composerType() {
        if (this.thread.model !== "discuss.channel") {
            return "note";
        }
        return undefined;
    }

    get hasActionsMenu() {
        return (
            this.partitionedActions.group.length > 0 ||
            this.partitionedActions.other.length > 0 ||
            (this.ui.isSmall && this.partitionedActions.quick.length > 2) ||
            (!this.ui.isSmall && this.partitionedActions.quick.length > 3)
        );
    }

    get thread() {
        return this.props.chatWindow.thread;
    }

    get showImStatus() {
        return this.thread?.channel_type === "chat" && this.thread.correspondent;
    }

    get attClass() {
        return {
            "w-100 h-100 o-mobile": this.ui.isSmall,
            "o-rounded-bubble border border-dark mb-2": !this.ui.isSmall,
        };
    }

    get style() {
        const textDirection = localization.direction;
        const offsetFrom = textDirection === "rtl" ? "left" : "right";
        const visibleOffset = this.ui.isSmall ? 0 : this.props.right;
        const oppositeFrom = offsetFrom === "right" ? "left" : "right";
        return `${offsetFrom}: ${visibleOffset}px; ${oppositeFrom}: auto;`;
    }

    onKeydown(ev) {
        const chatWindow = toRaw(this.props.chatWindow);
        if (ev.key === "Escape" && this.threadActions.activeAction) {
            this.threadActions.activeAction.close();
            ev.stopPropagation();
            return;
        }
        if (ev.target.closest(".o-dropdown") || ev.target.closest(".o-dropdown--menu")) {
            return;
        }
        ev.stopPropagation(); // not letting home menu steal my CTRL-C
        switch (getActiveHotkey(ev)) {
            case "escape":
                if (
                    isEventHandled(ev, "NavigableList.close") ||
                    isEventHandled(ev, "Composer.discard")
                ) {
                    return;
                }
                if (this.state.editingName) {
                    this.state.editingName = false;
                    return;
                }
                this.close({ escape: true });
                break;
            case "tab": {
                const index = this.store.chatHub.opened.findIndex((cw) => cw.eq(chatWindow));
                if (index === this.store.chatHub.opened.length - 1) {
                    this.store.chatHub.opened[0].focus({ jumpToNewMessage: true });
                } else {
                    this.store.chatHub.opened[index + 1].focus({ jumpToNewMessage: true });
                }
                break;
            }
            case "control+k":
                this.store.env.services.command.openMainPalette({ searchValue: "@" });
                ev.preventDefault();
                break;
        }
    }

    onClickHeader(ev) {
        if (
            this.ui.isSmall ||
            this.state.editingName ||
            this.props.chatWindow.actionsDisabled ||
            isEventHandled(ev, "ThreadAction.onSelected")
        ) {
            return;
        }
        this.toggleFold();
    }

    toggleFold() {
        const chatWindow = toRaw(this.props.chatWindow);
        if (this.state.actionsMenuOpened) {
            return;
        }
        chatWindow.fold();
    }

    close(options) {
        const chatWindow = toRaw(this.props.chatWindow);
        chatWindow.close(options);
    }

    get actionsMenuTitleText() {
        return _t("Open Actions Menu");
    }

    async renameThread(name) {
        const thread = toRaw(this.thread);
        await thread.rename(name);
        this.state.editingName = false;
    }

    async renameGuest(name) {
        const newName = name.trim();
        if (this.store.self.name !== newName) {
            await this.store.self.updateGuestName(newName);
        }
        this.state.editingGuestName = false;
    }

    async onActionsMenuStateChanged(isOpen) {
        // await new Promise(setTimeout); // wait for bubbling header
        this.state.actionsMenuOpened = isOpen;
    }
}
