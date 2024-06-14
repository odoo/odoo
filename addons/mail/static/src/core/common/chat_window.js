import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { Thread } from "@mail/core/common/thread";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import {
    useMessageEdition,
    useMessageHighlight,
    useMessageToReplyTo,
} from "@mail/utils/common/hooks";
import { isEventHandled } from "@web/core/utils/misc";

import { Component, toRaw, useChildSubEnv, useRef, useState } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Typing } from "@mail/discuss/typing/common/typing";

/**
 * @typedef {Object} Props
 * @property {import("models").ChatWindow} chatWindow
 * @property {boolean} [right]
 * @extends {Component<Props, Env>}
 */
export class ChatWindow extends Component {
    static components = {
        Dropdown,
        DropdownItem,
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
        this.store = useState(useService("mail.store"));
        this.messageEdition = useMessageEdition();
        this.messageHighlight = useMessageHighlight();
        this.messageToReplyTo = useMessageToReplyTo();
        this.state = useState({
            actionsMenuOpened: false,
            jumpThreadPresent: 0,
            editingName: false,
        });
        this.ui = useState(useService("ui"));
        this.contentRef = useRef("content");
        this.threadActions = useThreadActions();

        useChildSubEnv({
            closeActionPanel: () => this.threadActions.activeAction?.close(),
            inChatWindow: true,
            messageHighlight: this.messageHighlight,
        });
    }

    get composerType() {
        if (this.thread && this.thread.model !== "discuss.channel") {
            return "note";
        }
        return undefined;
    }

    get thread() {
        return this.props.chatWindow.thread;
    }

    get style() {
        const maxHeight = !this.ui.isSmall ? "max-height: 95vh;" : "";
        const textDirection = localization.direction;
        const offsetFrom = textDirection === "rtl" ? "left" : "right";
        const visibleOffset = this.ui.isSmall ? 0 : this.props.right;
        const oppositeFrom = offsetFrom === "right" ? "left" : "right";
        return `${offsetFrom}: ${visibleOffset}px; ${oppositeFrom}: auto; ${maxHeight}`;
    }

    onKeydown(ev) {
        const chatWindow = toRaw(this.props.chatWindow);
        if (ev.target.closest(".o-dropdown") || ev.target.closest(".o-dropdown--menu")) {
            return;
        }
        ev.stopPropagation(); // not letting home menu steal my CTRL-C
        switch (ev.key) {
            case "Escape":
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
            case "Tab": {
                const index = this.store.visibleChatWindows.findIndex((cw) => cw.eq(chatWindow));
                if (index === 0) {
                    this.store.visibleChatWindows.at(-1).autofocus++;
                } else {
                    this.store.visibleChatWindows[index - 1].autofocus++;
                }
                break;
            }
        }
    }

    onClickHeader() {
        if (!this.ui.isSmall && !this.state.editingName) {
            this.toggleFold();
        }
    }

    toggleFold() {
        const chatWindow = toRaw(this.props.chatWindow);
        if (this.ui.isSmall || this.state.actionsMenuOpened) {
            return;
        }
        if (chatWindow.hidden) {
            chatWindow.makeVisible();
        } else {
            chatWindow.toggleFold();
        }
    }

    async close(options) {
        const chatWindow = toRaw(this.props.chatWindow);
        await chatWindow.close(options);
    }

    get actionsMenuTitleText() {
        return _t("Open Actions Menu");
    }

    async renameThread(name) {
        const thread = toRaw(this.thread);
        await thread.rename(name);
        this.state.editingName = false;
    }

    async onActionsMenuStateChanged(isOpen) {
        // await new Promise(setTimeout); // wait for bubbling header
        this.state.actionsMenuOpened = isOpen;
    }
}
