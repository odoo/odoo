/* @odoo-module */

import { Thread } from "@mail/core_ui/thread";
import { Composer } from "@mail/composer/composer";
import { useStore } from "@mail/core/messaging_hook";
import { useThreadActions } from "@mail/core/thread_actions";
import { useMessageEdition, useMessageHighlight, useMessageToReplyTo } from "@mail/utils/hooks";
import { Component, useChildSubEnv, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { localization } from "@web/core/l10n/localization";
import { ThreadIcon } from "@mail/discuss_app/thread_icon";
import { ImStatus } from "@mail/discuss_app/im_status";
import { isEventHandled } from "@mail/utils/misc";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

/**
 * @typedef {Object} Props
 * @property {import("@mail/chat_window/chat_window_model").ChatWindow} chatWindow
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
    };
    static props = ["chatWindow", "right?"];
    static template = "mail.ChatWindow";

    setup() {
        this.store = useStore();
        /** @type {import("@mail/chat_window/chat_window_service").ChatWindowService} */
        this.chatWindowService = useState(useService("mail.chat_window"));
        /** @type {import("@mail/core/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
        this.messageEdition = useMessageEdition();
        this.messageHighlight = useMessageHighlight();
        this.messageToReplyTo = useMessageToReplyTo();
        this.state = useState({ moreActionsExpanded: false });
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
        switch (ev.key) {
            case "Escape":
                if (
                    isEventHandled(ev, "NavigableList.close") ||
                    isEventHandled(ev, "Composer.discard")
                ) {
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

    toggleFold() {
        if (this.ui.isSmall || this.state.moreActionsExpanded) {
            return;
        }
        if (this.props.chatWindow.hidden) {
            this.chatWindowService.makeVisible(this.props.chatWindow);
        } else {
            this.chatWindowService.toggleFold(this.props.chatWindow);
        }
        this.chatWindowService.notifyState(this.props.chatWindow);
    }

    close(options) {
        this.chatWindowService.close(this.props.chatWindow, options);
        this.chatWindowService.notifyState(this.props.chatWindow);
    }

    get moreMenuText() {
        return _t("More actions");
    }

    async onMoreActionsStateChanged(state) {
        await new Promise(setTimeout); // wait for bubbling header
        this.state.moreActionsExpanded = state.open;
    }
}
