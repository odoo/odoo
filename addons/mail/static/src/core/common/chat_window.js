// @ts-check
/** @odoo-module native */
import { ActionList } from "@mail/core/common/action_list";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { Composer } from "@mail/core/common/composer";
import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { Thread } from "@mail/core/common/thread";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { useHover, useMessageScrolling } from "@mail/utils/common/hooks";
import {
    Component,
    toRaw,
    useChildSubEnv,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/translation";
import { isEventHandled } from "@web/core/utils/dom/events";
import { useService } from "@web/core/utils/hooks";
const log = makeLogger("mail.chat_window");

/**
 * @typedef {Object} Props
 * @property {import("models").ChatWindow} chatWindow
 * @property {boolean} [right]
 * @extends {Component<Props, import("@web/env").OdooEnv>}
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
    };
    static props = ["chatWindow", "right?"];
    static template = "mail.ChatWindow";

    setup() {
        useLifecycleLog(log);
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

    get partitionedActions() {
        return this.threadActions.partition;
    }

    get autofocusComposer() {
        if (this.isMobileOS || this.thread.composerDisabled) {
            return undefined;
        }
        return this.props.chatWindow.autofocus;
    }

    get autofocusThread() {
        if (this.isMobileOS || this.thread.composerDisabled) {
            return this.props.chatWindow.autofocus;
        }
        return undefined;
    }

    get composerType() {
        return this.thread.chatWindowComposerType;
    }

    get hasActionsMenu() {
        const { group, other, quick } = this.partitionedActions;
        return (
            group.length > 0 ||
            other.length > 0 ||
            quick.length > (this.ui.isSmall ? 2 : 3)
        );
    }

    get thread() {
        return this.props.chatWindow.thread;
    }

    get showImStatus() {
        return Boolean(this.thread?.imStatusMember);
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

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        const chatWindow = toRaw(this.props.chatWindow);
        if (ev.key === "Escape" && this.threadActions.activeAction) {
            log.logic("Escape closes active action", () => ({
                thread: chatWindow.thread?.localId,
                action: this.threadActions.activeAction.id,
            }));
            this.threadActions.activeAction.close();
            ev.stopPropagation();
            return;
        }
        if (
            /** @type {Element} */ (ev.target).closest(".o-dropdown") ||
            /** @type {Element} */ (ev.target).closest(".o-dropdown--menu")
        ) {
            return;
        }
        ev.stopPropagation();
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
                const index = this.store.chatHub.opened.findIndex((cw) =>
                    cw.eq(chatWindow),
                );
                log.logic("tab to next chat window", () => ({
                    index,
                    opened: this.store.chatHub.opened.length,
                }));
                if (index === this.store.chatHub.opened.length - 1) {
                    this.store.chatHub.opened[0].focus({ jumpToNewMessage: true });
                } else {
                    this.store.chatHub.opened[index + 1].focus({
                        jumpToNewMessage: true,
                    });
                }
                break;
            }
            case "control+k":
                this.store.env.services.command.openMainPalette({ searchValue: "@" });
                ev.preventDefault();
                break;
        }
    }

    /** @param {MouseEvent} ev */
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

    /** @param {Object} [options] */
    close(options) {
        const chatWindow = toRaw(this.props.chatWindow);
        chatWindow.close(options);
    }

    get actionsMenuTitleText() {
        return _t("Open Actions Menu");
    }

    /** @param {string} name */
    async renameThread(name) {
        const thread = toRaw(this.thread);
        log.logic("renameThread", () => ({ thread: thread.localId, name }));
        await thread.rename(name);
        this.state.editingName = false;
    }

    cancelRenameThread() {
        this.state.editingName = false;
    }

    /** @param {string} name */
    async renameGuest(name) {
        const newName = name.trim();
        log.logic("renameGuest", () => ({
            changed: this.store.self.name !== newName,
        }));
        if (this.store.self.name !== newName) {
            await this.store.self_guest?.updateGuestName(newName);
        }
        this.state.editingGuestName = false;
    }

    cancelRenameGuest() {
        this.state.editingGuestName = false;
    }

    /** @param {boolean} isOpen */
    async onActionsMenuStateChanged(isOpen) {
        this.state.actionsMenuOpened = isOpen;
    }
}
