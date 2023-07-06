/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { useStore } from "@mail/core/common/messaging_hook";
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

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/chat_window_model").ChatWindow} chatWindow
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
    };
    static props = ["chatWindow", "right?"];
    static template = "mail.ChatWindow";

    setup() {
        this.store = useStore();
        /** @type {import("@mail/core/common/chat_window_service").ChatWindowService} */
        this.chatWindowService = useState(useService("mail.chat_window"));
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
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
            inChatWindow: true,
            messageHighlight: this.messageHighlight,
        });
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
                const index = this.chatWindowService.visible.findIndex(
                    (cw) => cw === this.props.chatWindow
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

    close(options) {
        this.chatWindowService.close(this.props.chatWindow, options);
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
