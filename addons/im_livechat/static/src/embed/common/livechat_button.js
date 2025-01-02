import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";
import { Component, useExternalListener, useRef, useState } from "@odoo/owl";

import { useMovable } from "@mail/utils/common/hooks";

import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

const LIVECHAT_BUTTON_SIZE = 56;

export class LivechatButton extends Component {
    static template = "im_livechat.LivechatButton";
    static props = {};
    static DEBOUNCE_DELAY = 500;

    setup() {
        this.store = useService("mail.store");
        /** @type {import('@im_livechat/embed/common/livechat_service').LivechatService} */
        this.livechatService = useService("im_livechat.livechat");
        this.onClick = debounce(this.onClick.bind(this), LivechatButton.DEBOUNCE_DELAY, {
            leading: true,
        });
        this.ref = useRef("button");
        this.size = LIVECHAT_BUTTON_SIZE;
        this.position = useState({
            left: `calc(97% - ${LIVECHAT_BUTTON_SIZE}px)`,
            top: `calc(97% - ${LIVECHAT_BUTTON_SIZE}px)`,
        });
        this.state = useState({
            animateNotification: !(
                this.livechatService.thread || this.livechatService.shouldRestoreSession
            ),
            hasAlreadyMovedOnce: false,
        });
        useMovable({
            cursor: "grabbing",
            ref: this.ref,
            elements: ".o-livechat-LivechatButton",
            onDrop: ({ top, left }) => {
                this.state.hasAlreadyMovedOnce = true;
                this.position.left = `${left}px`;
                this.position.top = `${top}px`;
            },
        });
        useExternalListener(document.body, "scroll", this._onScroll, { capture: true });
    }

    _onScroll(ev) {
        if (!this.ref.el || this.state.hasAlreadyMovedOnce) {
            return;
        }
        const container = ev.target;
        this.position.top =
            container.scrollHeight - container.scrollTop === container.clientHeight
                ? `calc(93% - ${LIVECHAT_BUTTON_SIZE}px)`
                : `calc(97% - ${LIVECHAT_BUTTON_SIZE}px)`;
    }

    onClick() {
        this.state.animateNotification = false;
        this.livechatService.open();
    }

    get isShown() {
        return (
            this.livechatService.initialized &&
            this.livechatService.available &&
            this.livechatService.state === SESSION_STATE.NONE &&
            Object.keys(this.store.ChatWindow.records).length === 0
        );
    }
}
