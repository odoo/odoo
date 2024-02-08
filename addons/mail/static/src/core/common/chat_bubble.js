import { ImStatus } from "@mail/core/common/im_status";

import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useHover, useMovable } from "@mail/utils/common/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubble extends Component {
    static components = { ImStatus, Dropdown };
    static props = ["chatWindow"];
    static template = "mail.ChatBubble";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.wasHover = false;
        this.hover = useHover(["root", "preview*"], () => {
            this.preview.isOpen = this.hover.isHover;
            if (this.hover.isHover && !this.wasHover) {
                clearTimeout(this.showCloseTimeout);
                this.showCloseTimeout = setTimeout(() => (this.state.showClose = true), 100);
            } else if (!this.hover.isHover) {
                clearTimeout(this.showCloseTimeout);
                this.state.showClose = false;
            }
            this.wasHover = this.hover.isHover;
        });
        this.preview = useDropdownState();
        this.rootRef = useRef("root");
        this.state = useState({ bouncing: false, showClose: true });
        useEffect(
            () => {
                this.state.bouncing = this.thread.importantCounter ? true : this.state.bouncing;
            },
            () => [this.thread.importantCounter]
        );
        if (this.env.embedLivechat) {
            this.position = useState({ left: "auto", top: "auto" });
            useMovable({
                cursor: "grabbing",
                ref: this.rootRef,
                elements: ".o-mail-ChatBubble",
                onDrop: ({ top, left }) =>
                    Object.assign(this.position, { left: `${left}px`, top: `${top}px` }),
            });
        }
    }

    /** @returns {import("models").Thread} */
    get thread() {
        return this.props.chatWindow.thread;
    }

    get previewContent() {
        const lastMessage = this.thread?.newestPersistentNotEmptyOfAllMessage;
        if (!lastMessage) {
            return false;
        }
        const selfAuthored = this.store.self.eq(lastMessage.author);
        return _t("%(authorName)s: %(body)s", {
            authorName: selfAuthored ? "You" : lastMessage.author.name,
            body: lastMessage.inlineBody,
        });
    }
}
