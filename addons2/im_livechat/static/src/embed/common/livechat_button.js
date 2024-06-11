/* @odoo-module */

import { Component, useRef, useState } from "@odoo/owl";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";

import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

const LIVECHAT_BUTTON_SIZE = 56;

const useMovable = makeDraggableHook({
    name: "useMovable",
    onWillStartDrag({ ctx, addCleanup, addStyle, getRect }) {
        const { height } = getRect(ctx.current.element);
        ctx.current.container = document.createElement("div");
        addStyle(ctx.current.container, {
            position: "fixed",
            top: 0,
            bottom: `${height}px`,
            left: 0,
            right: 0,
        });
        ctx.current.element.after(ctx.current.container);
        addCleanup(() => ctx.current.container.remove());
    },
    onDrop({ ctx, getRect }) {
        const { top, left } = getRect(ctx.current.element);
        return { top, left };
    },
});

export class LivechatButton extends Component {
    static template = "im_livechat.LivechatButton";
    static DEBOUNCE_DELAY = 500;

    setup() {
        this.store = useState(useService("mail.store"));
        /** @type {import('@im_livechat/embed/common/livechat_service').LivechatService} */
        this.livechatService = useState(useService("im_livechat.livechat"));
        /** @type {import('@mail/core/common/thread_service').ThreadService} */
        this.threadService = useService("mail.thread");
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
        });
        useMovable({
            cursor: "grabbing",
            ref: this.ref,
            elements: ".o-livechat-LivechatButton",
            onDrop: ({ top, left }) => {
                this.position.left = `${left}px`;
                this.position.top = `${top}px`;
            },
        });
    }

    onClick() {
        this.state.animateNotification = false;
        this.threadService.openChat();
    }

    get isShown() {
        return (
            this.livechatService.initialized &&
            this.livechatService.available &&
            !this.livechatService.shouldRestoreSession &&
            this.store.discuss.chatWindows.length === 0
        );
    }
}
