/* @odoo-module */

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

import { Component, useChildSubEnv, useRef, useState } from "@odoo/owl";

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
        this.store = useState(useService("mail.store"));
        this.chatWindowService = useState(useService("mail.chat_window"));
        this.threadService = useState(useService("mail.thread"));
        this.messageEdition = useMessageEdition();
        this.messageHighlight = useMessageHighlight();
        this.messageToReplyTo = useMessageToReplyTo();
        this.typingService = useState(useService("discuss.typing"));
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
        if (ev.key === "Escape" && this.threadActions.activeAction) {
            this.threadActions.activeAction.close();
            ev.stopPropagation();
            return;
        }
        if (ev.target.closest(".o-dropdown")) {
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
                const index = this.chatWindowService.visible.findIndex((cw) =>
                    cw.eq(this.props.chatWindow)
                );
                if (index === 0) {
                    this.chatWindowService.visible[this.chatWindowService.visible.length - 1]
                        .autofocus++;
                } else {
                    this.chatWindowService.visible[index - 1].autofocus++;
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
        if (this.ui.isSmall || this.state.actionsMenuOpened) {
            return;
        }
        if (this.props.chatWindow.hidden) {
            this.chatWindowService.makeVisible(this.props.chatWindow);
        } else {
            this.chatWindowService.toggleFold(this.props.chatWindow);
        }
    }

    async close(options) {
        await this.chatWindowService.close(this.props.chatWindow, options);
    }

    get actionsMenuTitleText() {
        return _t("Open Actions Menu");
    }

    async renameThread(name) {
        await this.threadService.renameThread(this.thread, name);
        this.state.editingName = false;
    }

    async onActionsMenuStateChanged(state) {
        await new Promise(setTimeout); // wait for bubbling header
        this.state.actionsMenuOpened = state.open;
    }
}
